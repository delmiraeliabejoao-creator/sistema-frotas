from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = "chave_secreta_segura_123456"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///banco_pendencias.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configurações para upload de fotos
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Limite de 16MB por arquivo

# Cria pasta de uploads se não existir
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

db = SQLAlchemy(app)

# Função auxiliar para verificar tipo de arquivo
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ------------------- MODELOS -------------------
class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    senha = db.Column(db.String(200), nullable=False)
    funcao = db.Column(db.String(100))
    nivel_acesso = db.Column(db.String(50), nullable=False)

class Maquina(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    codigo_interno = db.Column(db.String(50), unique=True, nullable=False)
    modelo = db.Column(db.String(150), nullable=False)
    ano = db.Column(db.Integer)
    numero_serie = db.Column(db.String(100))
    placa = db.Column(db.String(20))
    horimetro = db.Column(db.Float, default=0.0)
    localizacao = db.Column(db.String(100))
    tipo_frota = db.Column(db.String(50), nullable=False)

class TipoServico(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    descricao = db.Column(db.String(100), nullable=False)

class OrdemServico(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    numero_os = db.Column(db.String(20), unique=True, nullable=False)
    maquina_id = db.Column(db.Integer, db.ForeignKey('maquina.id'), nullable=False)
    tipo_servico_id = db.Column(db.Integer, db.ForeignKey('tipo_servico.id'), nullable=False)
    descricao = db.Column(db.Text, nullable=False)
    horimetro = db.Column(db.Float, nullable=False)
    prioridade = db.Column(db.String(20), default="Média")
    status = db.Column(db.String(50), default="Aguardando Serviço")
    data_abertura = db.Column(db.DateTime, default=datetime.utcnow)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'))
    fotos = db.Column(db.Text)  # Armazena caminhos das fotos separados por vírgula

    maquina = db.relationship('Maquina', backref=db.backref('ordens', lazy=True))
    tipo_servico = db.relationship('TipoServico', backref=db.backref('ordens', lazy=True))
    usuario = db.relationship('Usuario', backref=db.backref('ordens', lazy=True))

class SolicitacaoPeca(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ordem_servico_id = db.Column(db.Integer, db.ForeignKey('ordem_servico.id'), nullable=False)
    nome_peca = db.Column(db.String(150), nullable=False)
    codigo_peca = db.Column(db.String(100))
    quantidade = db.Column(db.Integer, nullable=False)
    modulo = db.Column(db.String(100))
    motivo = db.Column(db.String(200))
    observacao = db.Column(db.Text)
    status = db.Column(db.String(50), default="Aguardando Peça Chegar na Base")
    data_solicitacao = db.Column(db.DateTime, default=datetime.utcnow)
    nome_solicitante = db.Column(db.String(100))

    ordem_servico = db.relationship('OrdemServico', backref=db.backref('pecas', lazy=True))

class HistoricoPeca(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    solicitacao_id = db.Column(db.Integer, db.ForeignKey('solicitacao_peca.id'), nullable=False)
    status_anterior = db.Column(db.String(50))
    status_novo = db.Column(db.String(50), nullable=False)
    observacao = db.Column(db.Text)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'))
    data_alteracao = db.Column(db.DateTime, default=datetime.utcnow)

    solicitacao = db.relationship('SolicitacaoPeca', backref=db.backref('historico', lazy=True))
    usuario = db.relationship('Usuario', backref=db.backref('alteracoes_pecas', lazy=True))

# ------------------- ROTAS -------------------
@app.route('/')
def index():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    abertas = OrdemServico.query.filter_by(status="Aguardando Serviço").count()
    aguardando_peca = OrdemServico.query.filter_by(status="Aguardando Peça").count()
    liberadas = OrdemServico.query.filter_by(status="Liberado com Pendência").count()
    concluidas = OrdemServico.query.filter_by(status="Concluída").count()
    return render_template('painel.html', abertas=abertas, aguardando_peca=aguardando_peca, liberadas=liberadas, concluidas=concluidas)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        senha = request.form.get('senha')
        usuario = Usuario.query.filter_by(email=email).first()
        if usuario and check_password_hash(usuario.senha, senha):
            session['usuario_id'] = usuario.id
            session['nome_usuario'] = usuario.nome
            session['nivel_acesso'] = usuario.nivel_acesso
            flash('Login realizado com sucesso!')
            return redirect(url_for('index'))
        flash('E-mail ou senha incorretos!')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Sessão encerrada.')
    return redirect(url_for('login'))

@app.route('/cadastrar-maquina', methods=['GET', 'POST'])
def cadastrar_maquina():
    if 'usuario_id' not in session or session['nivel_acesso'] not in ['Administrador', 'Gerente', 'Supervisor Manutenção', 'Supervisor de Operação']:
        flash('Acesso negado!')
        return redirect(url_for('index'))
    if request.method == 'POST':
        nova = Maquina(
            codigo_interno=request.form.get('codigo'),
            modelo=request.form.get('modelo'),
            ano=request.form.get('ano'),
            numero_serie=request.form.get('serie'),
            placa=request.form.get('placa'),
            horimetro=float(request.form.get('horimetro') or 0),
            localizacao=request.form.get('localizacao'),
            tipo_frota=request.form.get('tipo_frota')
        )
        try:
            db.session.add(nova)
            db.session.commit()
            flash(f'Equipamento cadastrado com sucesso na {nova.tipo_frota}!')
        except:
            flash('Erro: Código interno já existe!')
        return redirect(url_for('cadastrar_maquina'))
    return render_template('cadastrar_maquina.html')

@app.route('/abrir-os', methods=['GET', 'POST'])
def abrir_os():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        ultima_os = OrdemServico.query.order_by(OrdemServico.id.desc()).first()
        numero = f"OS-{datetime.now().strftime('%Y%m')}-{ultima_os.id + 1 if ultima_os else 1:04d}"

        # Processa upload de fotos
        fotos_salvas = []
        arquivos = request.files.getlist('fotos')
        
        for arquivo in arquivos:
            if arquivo and allowed_file(arquivo.filename):
                nome_seguro = secure_filename(f"{numero}_{datetime.now().strftime('%H%M%S')}_{arquivo.filename}")
                caminho_completo = os.path.join(app.config['UPLOAD_FOLDER'], nome_seguro)
                arquivo.save(caminho_completo)
                fotos_salvas.append(nome_seguro)

        fotos_texto = ",".join(fotos_salvas) if fotos_salvas else None

        nova_os = OrdemServico(
            numero_os=numero,
            maquina_id=request.form.get('maquina_id'),
            tipo_servico_id=request.form.get('tipo_id'),
            descricao=request.form.get('descricao'),
            horimetro=float(request.form.get('horimetro')),
            prioridade=request.form.get('prioridade'),
            usuario_id=session['usuario_id'],
            fotos=fotos_texto
        )

        db.session.add(nova_os)
        db.session.commit()
        flash(f'Ordem de Serviço {numero} aberta com sucesso! {len(fotos_salvas)} foto(s) anexada(s).')
        return redirect(url_for('listar_os'))

    maquinas = Maquina.query.all()
    tipos = TipoServico.query.all()
    return render_template('abrir_os.html', maquinas=maquinas, tipos=tipos)

@app.route('/uploads/<nome_arquivo>')
def ver_foto(nome_arquivo):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    return send_from_directory(app.config['UPLOAD_FOLDER'], nome_arquivo)

@app.route('/listar-os')
def listar_os():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    ordens = OrdemServico.query.order_by(OrdemServico.data_abertura.desc()).all()
    return render_template('listar_os.html', ordens=ordens)

@app.route('/alterar-status/<int:os_id>', methods=['POST'])
def alterar_status(os_id):
    if 'usuario_id' not in session or session['nivel_acesso'] not in ['Supervisor Manutenção', 'Supervisor de Operação', 'Coordenador', 'Gerente', 'Administrador']:
        flash('Sem permissão!')
        return redirect(url_for('listar_os'))
    os = OrdemServico.query.get_or_404(os_id)
    os.status = request.form.get('status')
    db.session.commit()
    flash('Status atualizado!')
    return redirect(url_for('listar_os'))

@app.route('/solicitar-pecas/<int:os_id>', methods=['GET', 'POST'])
def solicitar_pecas(os_id):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    os = OrdemServico.query.get_or_404(os_id)
    if request.method == 'POST':
        nova_sol = SolicitacaoPeca(
            ordem_servico_id=os_id,
            nome_peca=request.form.get('nome_peca'),
            codigo_peca=request.form.get('codigo_peca'),
            quantidade=int(request.form.get('quantidade')),
            modulo=request.form.get('modulo'),
            motivo=request.form.get('motivo'),
            observacao=request.form.get('observacao'),
            nome_solicitante=session['nome_usuario']
        )
        db.session.add(nova_sol)
        db.session.commit()
        flash('Solicitação enviada ao almoxarifado!')
        return redirect(url_for('listar_os'))
    return render_template('solicitar_pecas.html', ordem=os)

@app.route('/almoxarifado')
def almoxarifado():
    if 'usuario_id' not in session or session['nivel_acesso'] not in ['Almoxarifado', 'Supervisor Manutenção', 'Supervisor de Operação', 'Gerente', 'Administrador']:
        flash('Acesso restrito!')
        return redirect(url_for('index'))
    solicitacoes = SolicitacaoPeca.query.order_by(SolicitacaoPeca.data_solicitacao.desc()).all()
    return render_template('almoxarifado.html', solicitacoes=solicitacoes)

@app.route('/atualizar-peca/<int:sol_id>', methods=['POST'])
def atualizar_peca(sol_id):
    if 'usuario_id' not in session or session['nivel_acesso'] not in ['Almoxarifado', 'Supervisor Manutenção', 'Gerente', 'Administrador']:
        flash('Sem permissão!')
        return redirect(url_for('almoxarifado'))
    sol = SolicitacaoPeca.query.get_or_404(sol_id)
    antigo = sol.status
    novo = request.form.get('novo_status')
    sol.status = novo
    hist = HistoricoPeca(
        solicitacao_id=sol_id,
        status_anterior=antigo,
        status_novo=novo,
        observacao=request.form.get('observacao'),
        usuario_id=session['usuario_id']
    )
    db.session.add(hist)
    db.session.commit()
    flash('Status atualizado!')
    return redirect(url_for('almoxarifado'))

@app.route('/historico-peca/<int:sol_id>')
def historico_peca(sol_id):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    sol = SolicitacaoPeca.query.get_or_404(sol_id)
    historico = HistoricoPeca.query.filter_by(solicitacao_id=sol_id).order_by(HistoricoPeca.data_alteracao.desc()).all()
    return render_template('historico_peca.html', solicitacao=sol, historico=historico)

@app.route('/listar-usuarios')
def listar_usuarios():
    if 'usuario_id' not in session or session['nivel_acesso'] != 'Administrador':
        flash('Acesso exclusivo para administrador!')
        return redirect(url_for('index'))
    usuarios = Usuario.query.all()
    return render_template('listar_usuarios.html', usuarios=usuarios)

@app.route('/cadastrar-usuario', methods=['GET', 'POST'])
def cadastrar_usuario():
    if 'usuario_id' not in session or session['nivel_acesso'] != 'Administrador':
        flash('Acesso negado!')
        return redirect(url_for('index'))
    if request.method == 'POST':
        novo = Usuario(
            nome=request.form.get('nome'),
            email=request.form.get('email'),
            senha=generate_password_hash(request.form.get('senha')),
            funcao=request.form.get('funcao'),
            nivel_acesso=request.form.get('nivel')
        )
        try:
            db.session.add(novo)
            db.session.commit()
            flash('Usuário cadastrado!')
        except:
            flash('E-mail já cadastrado!')
        return redirect(url_for('listar_usuarios'))
    perfis = ['Mecânico','Operador', 'Almoxarifado', 'Supervisor Manutenção', 'Supervisor de Operação', 'Coordenador', 'Gerente', 'Administrador']
    return render_template('cadastrar_usuario.html', perfis=perfis)

@app.route('/alterar-senha-usuario/<int:user_id>', methods=['POST'])
def alterar_senha_usuario(user_id):
    if 'usuario_id' not in session or session['nivel_acesso'] != 'Administrador':
        return redirect(url_for('index'))
    usuario = Usuario.query.get_or_404(user_id)
    nova_senha = request.form.get('nova_senha')
    usuario.senha = generate_password_hash(nova_senha)
    db.session.commit()
    flash('Senha atualizada!')
    return redirect(url_for('listar_usuarios'))

# ------------------- INICIALIZAÇÃO -------------------
with app.app_context():
    db.create_all()
    if not Usuario.query.filter_by(email="admin@frota.com").first():
        admin = Usuario(
            nome="Administrador",
            email="admin@frota.com",
            senha=generate_password_hash("123456"),
            funcao="Gestor do Sistema",
            nivel_acesso="Administrador"
        )
        db.session.add(admin)
    if not TipoServico.query.first():
        tipos = [
            "Manutenção Preventiva",
            "Manutenção Corretiva",
            "Revisão Geral",
            "Troca de Peças",
            "Reparo de Sistema",
            "Inspeção Técnica"
        ]
        for t in tipos:
            db.session.add(TipoServico(descricao=t))
    db.session.commit()

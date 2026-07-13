from extensions import db
from datetime import datetime

class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    funcao = db.Column(db.String(80))
    email = db.Column(db.String(120), unique=True, nullable=False)
    senha_hash = db.Column(db.String(256), nullable=False)
    nivel_acesso = db.Column(db.String(50), nullable=False)
    ativo = db.Column(db.Boolean, default=True)
    token_recuperacao = db.Column(db.String(100))
    validade_token = db.Column(db.DateTime)

class Maquina(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    codigo_interno = db.Column(db.String(30), unique=True, nullable=False)
    modelo = db.Column(db.String(100), nullable=False)
    ano_fabricacao = db.Column(db.Integer)
    numero_serie = db.Column(db.String(100))
    placa = db.Column(db.String(20))
    horimetro_atual = db.Column(db.Float, default=0.0)
    localizacao = db.Column(db.String(100))
    data_cadastro = db.Column(db.DateTime, default=datetime.utcnow)

class TipoServico(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    descricao = db.Column(db.String(100), nullable=False)

class OrdemServico(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    numero_os = db.Column(db.String(10), unique=True, nullable=False)
    maquina_id = db.Column(db.Integer, db.ForeignKey("maquina.id"), nullable=False)
    tipo_servico_id = db.Column(db.Integer, db.ForeignKey("tipo_servico.id"), nullable=False)
    descricao = db.Column(db.Text, nullable=False)
    horimetro = db.Column(db.Float)
    prioridade = db.Column(db.String(20), default="Média")
    prazo_limite = db.Column(db.DateTime)
    status = db.Column(db.String(50), default="Aguardando Serviço")
    data_abertura = db.Column(db.DateTime, default=datetime.utcnow)
    data_fechamento = db.Column(db.DateTime)
    usuario_abertura_id = db.Column(db.Integer, db.ForeignKey("usuario.id"))

    maquina = db.relationship("Maquina", backref=db.backref("ordens", lazy=True))
    tipo_servico = db.relationship("TipoServico", backref=db.backref("ordens", lazy=True))
    usuario_abertura = db.relationship("Usuario", backref=db.backref("ordens_abertas", lazy=True))

class SolicitacaoPeca(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ordem_servico_id = db.Column(db.Integer, db.ForeignKey("ordem_servico.id"), nullable=False)
    nome_peca = db.Column(db.String(150), nullable=False)
    codigo_peca = db.Column(db.String(100))
    quantidade = db.Column(db.Integer, nullable=False)
    modulo = db.Column(db.String(100))
    motivo = db.Column(db.String(200))
    observacao = db.Column(db.Text)
    nome_mecanico = db.Column(db.String(100))
    status = db.Column(db.String(60), default="Aguardando Peça Chegar na Base")
    data_solicitacao = db.Column(db.DateTime, default=datetime.utcnow)

    ordem_servico = db.relationship("OrdemServico", backref=db.backref("pecas_solicitadas", lazy=True))

class HistoricoPeca(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    solicitacao_peca_id = db.Column(db.Integer, db.ForeignKey("solicitacao_peca.id"), nullable=False)
    status_anterior = db.Column(db.String(60))
    novo_status = db.Column(db.String(60), nullable=False)
    observacao = db.Column(db.Text)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuario.id"))
    data_hora = db.Column(db.DateTime, default=datetime.utcnow)

    solicitacao = db.relationship("SolicitacaoPeca", backref=db.backref("historico", lazy=True))
    usuario = db.relationship("Usuario", backref=db.backref("atualizacoes_pecas", lazy=True))

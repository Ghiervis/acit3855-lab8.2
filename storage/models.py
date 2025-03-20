from sqlalchemy import create_engine, Column, Integer, String, DateTime, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import yaml

# Load database configuration
with open("app_conf.yml", "r") as f:
    app_config = yaml.safe_load(f.read())

db_user = app_config["datastore"]["user"]
db_password = app_config["datastore"]["password"]
db_host = app_config["datastore"]["hostname"]
db_port = app_config["datastore"]["port"]
db_name = app_config["datastore"]["db"]

engine = create_engine(f'mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}')
Session = sessionmaker(bind=engine)

Base = declarative_base()

class PlayerPerformance(Base):
    __tablename__ = 'player_perf'
    id = Column(Integer, primary_key=True, autoincrement=True)
    player_id = Column(String(50), nullable=False)
    score = Column(Integer, nullable=False)
    numeric_value = Column(Integer, nullable=False)
    trace_id = Column(String(50), nullable=False)
    uuid = Column(String(50), nullable=False)
    date_created = Column(DateTime, default=func.now())

    def __init__(self, player_id, score, uuid, numeric_value, trace_id):
        self.player_id = player_id
        self.score = score
        self.uuid = uuid
        self.numeric_value = numeric_value
        self.trace_id = trace_id

    def to_dict(self):
        return {
            "playerId": self.player_id,
            "score": self.score,
            "trace_id": self.trace_id,
            "uuid": self.uuid,
            "numeric_value": self.numeric_value,
            "date_created": self.date_created.isoformat() if self.date_created else None
        }

class AudienceInteraction(Base):
    __tablename__ = 'audience'
    id = Column(Integer, primary_key=True, autoincrement=True)
    interactionType = Column(String(50), nullable=False)
    trace_id = Column(String(50), nullable=False)
    uuid = Column(String(50), nullable=False)
    numeric_value = Column(Integer, nullable=False)
    date_created = Column(DateTime, default=func.now())

    def __init__(self, interactionType, trace_id, uuid, numeric_value):
        self.interactionType = interactionType
        self.trace_id = trace_id
        self.uuid = uuid
        self.numeric_value = numeric_value

    def to_dict(self):
        return {
            "interactionType": self.interactionType,
            "trace_id": self.trace_id,
            "uuid": self.uuid,
            "numeric_value": self.numeric_value,
            "date_created": self.date_created.isoformat() if self.date_created else None
        }

def init_db():
    Base.metadata.create_all(engine)

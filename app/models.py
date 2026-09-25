from datetime import datetime, timezone
from .extensions import db


class Word(db.Model):
    __tablename__ = "words"

    id = db.Column(db.Integer, primary_key=True)
    english = db.Column(db.String(200), nullable=False, unique=True)
    spanish = db.Column(db.String(200), nullable=False)
    notes = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    stats = db.relationship("WordStats", uselist=False, cascade="all, delete-orphan")
    history = db.relationship("SessionHistory", lazy="dynamic", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Word {self.english} = {self.spanish}>"


class WordStats(db.Model):
    __tablename__ = "word_stats"

    id = db.Column(db.Integer, primary_key=True)
    word_id = db.Column(db.Integer, db.ForeignKey("words.id"), nullable=False, unique=True)
    repetitions = db.Column(db.Integer, default=0)
    easiness_factor = db.Column(db.Float, default=2.5)
    interval = db.Column(db.Integer, default=0)
    times_practiced = db.Column(db.Integer, default=0)
    times_correct = db.Column(db.Integer, default=0)
    level = db.Column(db.Integer, default=0)
    next_review = db.Column(db.DateTime, nullable=True)
    last_practiced = db.Column(db.DateTime, nullable=True)

    @property
    def accuracy(self):
        if self.times_practiced == 0:
            return 0
        return round(self.times_correct / self.times_practiced * 100)

    @property
    def level_name(self):
        names = {0: "Nueva", 1: "Facil", 2: "Media", 3: "Dificil"}
        return names.get(self.level, "Nueva")

    @property
    def level_color(self):
        colors = {0: "secondary", 1: "success", 2: "warning", 3: "danger"}
        return colors.get(self.level, "secondary")


class SessionHistory(db.Model):
    __tablename__ = "session_history"

    id = db.Column(db.Integer, primary_key=True)
    word_id = db.Column(db.Integer, db.ForeignKey("words.id"), nullable=False)
    english_answer = db.Column(db.String(200))
    sentence = db.Column(db.Text)
    sentence_details = db.Column(db.Text, nullable=True)
    is_correct = db.Column(db.Boolean, default=False)
    sentence_valid = db.Column(db.Boolean, default=False)
    score = db.Column(db.Integer, default=0)
    quality = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    session_type = db.Column(db.String(20), nullable=False, server_default="quiz")
    direction = db.Column(db.String(20), nullable=False, server_default="es_to_en")
    validator_source = db.Column(db.String(10), nullable=False, server_default="spacy")
    sentence_suggestion = db.Column(db.Text, nullable=True)
    was_revealed = db.Column(db.Boolean, nullable=False, server_default="0", default=False)

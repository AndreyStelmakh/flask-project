import typing
import pydantic
from flask import Flask, jsonify, request
from flask.views import MethodView
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import Column, Integer, String, DateTime, func, create_engine


class HttpError(Exception):
    def __init__(self, status_code: int, message):
        self.status_code = status_code
        self.message = message


class CreateAnnouncement(pydantic.BaseModel):
    header: str
    description: str
    owner: str


class PatchAnnouncement(pydantic.BaseModel):
    header: typing.Optional[str]
    description: typing.Optional[str]
    owner: typing.Optional[str]


def validate(model, raw_data: dict):
    try:
        return model(**raw_data).dict()
    except pydantic.ValidationError as error:
        raise HttpError(400, error.errors())


app = Flask("app")


@app.errorhandler(HttpError)
def http_error_handler(error: HttpError):
    response = jsonify({
        'status': 'error',
        'reason': error.message
    })
    response.status_code = error.status_code
    return response


Base = declarative_base()

PG_DSN = 'postgresql://app:1234@127.0.0.1/flask'
engine = create_engine(PG_DSN)
Session = sessionmaker(bind=engine)


class Announcement(Base):
    __tablename__ = 'announcement'

    id = Column(Integer, primary_key=True)
    header = Column(String, nullable=False)
    description = Column(String)
    created_at = Column(DateTime, server_default=func.now())
    owner = Column(String)
    pass


def get_announcement(session: Session, announcement_id: id):
    announcement = session.query(Announcement).get(announcement_id)
    if announcement is None:
        raise HttpError(404, 'Announcement not found')
    return announcement


Base.metadata.create_all(engine)


class AnnouncementView(MethodView):
    def get(self, announcement_id: int):
        with Session() as session:
            announcement = get_announcement(session, announcement_id)
        return jsonify({'header': announcement.header,
                        'description': announcement.description,
                        'created_at': announcement.created_at.isoformat(),
                        'owner': announcement.owner})

    def post(self):
        validated = validate(CreateAnnouncement, request.json)
        with Session() as session:
            announcement = Announcement(header=validated['header'],
                                        description=validated['description'],
                                        owner=validated['owner'])
            session.add(announcement)
            session.commit()

    def patch(self, announcement_id: int):
        validated = validate(PatchAnnouncement, request.json)
        with Session() as session:
            announcement = get_announcement(session, announcement_id)
            if validated.get("header"):
                announcement.header = validated["header"]
            if validated.get("description"):
                announcement.header = validated["description"]
            if validated.get("owner"):
                announcement.header = validated["owner"]
            session.add(announcement)
            session.commit()
        return {'status': 'success'}

    def delete(self, announcement_id: int):
        with Session() as session:
            announcement = get_announcement(session, announcement_id)
            session.delete(announcement)
            session.commit()
        return {'status': 'success'}


announcement_view = AnnouncementView.as_view('announcements')
app.add_url_rule('/announcements/', view_func=announcement_view, methods=['POST'])
app.add_url_rule('/announcements/<int:announcement_id>', view_func=announcement_view, methods=['GET', 'PATCH', 'DELETE'])

app.run()

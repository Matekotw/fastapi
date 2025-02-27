from sqlalchemy import create_engine,text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from ..database import Base
from ..main import app
from ..routers.todos import get_db,get_current_user
from fastapi.testclient import TestClient
from fastapi import status
import pytest
from ..models import Todos

SQLALCHEMY_DATABASE = "sqlite:///./testdb.db"



engine = create_engine(

    SQLALCHEMY_DATABASE,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def override_get_current_user():
    return {'username': 'kamiltest', 'id': 1, 'user_role': 'admin'}


app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_current_user] = override_get_current_user

client = TestClient(app)

@pytest.fixture
def test_todo():
    todo = Todos(title="test",
                 description="test",
                 priority=5,
                 complete=False,
                 owner_id=1,
                 )

    db = TestingSessionLocal()
    db.add(todo)
    db.commit()
    yield todo
    with engine.connect() as connection:
        connection.execute(text("DELETE FROM todos;"))
        connection.commit()

def test_read_all_authenticated(test_todo):
    response = client.get("/todos")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == [{'complete': False,
                                'id': 1,
                                'title': 'test',
                                'description': 'test',
                                'priority': 5,
                                'owner_id': 1}]


def test_read_one_authenticated(test_todo):
    response = client.get("todos/todo/1")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == [{'complete': False,
                                'id': 1,
                                'title': 'test',
                                'description': 'test',
                                'priority': 5,
                                'owner_id': 1}]


def test_read_one_authenticated_not_found(test_todo):
    response = client.get("todos/todo/999")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {'detail': 'Todo Not found.'}


def test_create_todo(test_todo):
    request_data = {"title": "new todo!",
                    "description": "new description",
                    "priority": 5,
                    "complete": False,
                }
    response = client.post("/todo/", json=request_data)
    assert response.status_code == status.HTTP_201_CREATED


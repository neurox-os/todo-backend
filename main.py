from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
import datetime
# Import components from your newly created files
import models
import schemas
from database import engine, SessionLocal

import os
from dotenv import load_dotenv

load_dotenv()


SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
# Create tables in the database automatically
models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# Enable CORS for the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

def get_password_hash(password):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    
    user = db.query(models.DBUser).filter(models.DBUser.username == username).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user

# ==========================================
# ENDPOINTS
# ==========================================
@app.post("/register")
def register(user: schemas.UserRegister, db: Session = Depends(get_db)):
    if db.query(models.DBUser).filter(models.DBUser.username == user.username).first():
        raise HTTPException(status_code=400, detail="Username already registered")
    
    hashed_pwd = get_password_hash(user.password)
    new_user = models.DBUser(username=user.username, email=user.email, hashed_password=hashed_pwd)
    db.add(new_user)
    db.commit()
    
    access_token = create_access_token(data={"sub": new_user.username})
    return {"access_token": access_token}

@app.post("/login")
def login(user: schemas.UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(models.DBUser).filter(models.DBUser.username == user.username).first()
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    
    access_token = create_access_token(data={"sub": db_user.username})
    return {"access_token": access_token}

@app.get("/tasks", response_model=list[schemas.TaskOut])
def get_tasks(current_user: models.DBUser = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(models.DBTask).filter(models.DBTask.user_id == current_user.id).order_by(models.DBTask.id).all()

@app.post("/tasks", response_model=schemas.TaskOut)
def create_task(task: schemas.TaskCreate, current_user: models.DBUser = Depends(get_current_user), db: Session = Depends(get_db)):
    new_task = models.DBTask(text=task.text, user_id=current_user.id)
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return new_task

@app.put("/tasks/{task_id}", response_model=schemas.TaskOut)
def update_task(task_id: int, task_update: schemas.TaskUpdate, current_user: models.DBUser = Depends(get_current_user), db: Session = Depends(get_db)):
    db_task = db.query(models.DBTask).filter(models.DBTask.id == task_id, models.DBTask.user_id == current_user.id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task_update.text is not None:
        db_task.text = task_update.text
    if task_update.completed is not None:
        db_task.completed = task_update.completed
        
    db.commit()
    db.refresh(db_task)
    return db_task

@app.delete("/tasks/{task_id}")
def delete_task(task_id: int, current_user: models.DBUser = Depends(get_current_user), db: Session = Depends(get_db)):
    db_task = db.query(models.DBTask).filter(models.DBTask.id == task_id, models.DBTask.user_id == current_user.id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    db.delete(db_task)
    db.commit()
    return {"detail": "Task deleted successfully"}
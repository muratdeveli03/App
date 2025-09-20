from fastapi import FastAPI, APIRouter, HTTPException, UploadFile, File
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, date
import csv
import io
import hashlib

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Security
security = HTTPBearer()

# Models
class Student(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    code: str
    name: str
    class_name: str

class StudentCreate(BaseModel):
    code: str
    name: str
    class_name: str

class Word(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    class_name: str
    english: str
    turkish: str  # Noktalı virgülle ayrılan çoklu anlam

class WordCreate(BaseModel):
    class_name: str
    english: str
    turkish: str

class StudentProgress(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    student_code: str
    word_id: str
    box_number: int  # 1-5 arası kutu numarası
    last_studied_date: str  # ISO format date
    correct_count: int = 0
    wrong_count: int = 0

class StudySession(BaseModel):
    student_code: str
    word_id: str
    answer: str
    is_correct: bool

class LoginRequest(BaseModel):
    code: str

class AdminLoginRequest(BaseModel):
    password: str

class QuizWord(BaseModel):
    word_id: str
    english: str
    turkish: str
    box_number: int

class StudentStats(BaseModel):
    total_words: int
    box1_words: int
    box2_words: int
    box3_words: int
    box4_words: int
    box5_words: int
    studied_today: int

def get_today_date():
    """Bugünün tarihini ISO format string olarak döndürür"""
    return date.today().isoformat()

def check_answer(student_answer: str, correct_answers: str) -> bool:
    """Öğrenci cevabını kontrol eder. Çoklu cevapları noktalı virgülle ayrılmış şekilde destekler"""
    student_answer = student_answer.strip().lower()
    answers = [answer.strip().lower() for answer in correct_answers.split(';')]
    return student_answer in answers

async def get_next_word_for_student(student_code: str) -> Optional[Dict[str, Any]]:
    """5 kutu yöntemiyle öğrenci için sonraki kelimeyi getirir"""
    # Öğrenciyi bul
    student = await db.students.find_one({"code": student_code})
    if not student:
        return None
    
    today = get_today_date()
    
    # Bu öğrencinin sınıfındaki tüm kelimeleri al
    words = await db.words.find({"class_name": student["class_name"]}).to_list(None)
    if not words:
        return None
    
    # Öğrencinin kelime ilerlemelerini al
    progress_records = await db.student_progress.find({"student_code": student_code}).to_list(None)
    progress_dict = {record["word_id"]: record for record in progress_records}
    
    # Bugün çalışılmamış kelimeleri bul ve kutu numarasına göre sınıflandır
    words_by_box = {1: [], 2: [], 3: [], 4: [], 5: []}
    
    for word in words:
        word_id = word["id"]
        progress = progress_dict.get(word_id)
        
        if progress is None:
            # Yeni kelime - 1. kutuda başla
            words_by_box[1].append(word)
        elif progress["last_studied_date"] != today:
            # Bugün çalışılmamış - mevcut kutusuna ekle
            box_num = progress["box_number"]
            words_by_box[box_num].append(word)
    
    # En ilerideki kutudan başlayarak kelime seç (5. kutu hariç)
    for box_num in [4, 3, 2, 1]:
        if words_by_box[box_num]:
            selected_word = words_by_box[box_num][0]  # İlk kelimeyi seç
            return {
                "word_id": selected_word["id"],
                "english": selected_word["english"],
                "turkish": selected_word["turkish"],
                "box_number": progress_dict.get(selected_word["id"], {}).get("box_number", 1)
            }
    
    # Eğer 5. kutuda kelime varsa ve diğer kutularda kelime kalmadıysa
    if words_by_box[5]:
        selected_word = words_by_box[5][0]
        return {
            "word_id": selected_word["id"],
            "english": selected_word["english"],
            "turkish": selected_word["turkish"],
            "box_number": 5
        }
    
    return None  # Bugün için tüm kelimeler çalışıldı

async def update_word_progress(student_code: str, word_id: str, is_correct: bool):
    """Kelime ilerlemesini günceller"""
    today = get_today_date()
    
    # Mevcut ilerlemeyi bul
    progress = await db.student_progress.find_one({"student_code": student_code, "word_id": word_id})
    
    if progress is None:
        # Yeni ilerleme kaydı oluştur
        new_box = 2 if is_correct else 1
        new_progress = StudentProgress(
            student_code=student_code,
            word_id=word_id,
            box_number=new_box,
            last_studied_date=today,
            correct_count=1 if is_correct else 0,
            wrong_count=0 if is_correct else 1
        )
        await db.student_progress.insert_one(new_progress.dict())
    else:
        # Mevcut ilerlemeyi güncelle
        current_box = progress["box_number"]
        
        if is_correct:
            new_box = min(5, current_box + 1)  # Maksimum 5. kutu
            new_correct = progress["correct_count"] + 1
            new_wrong = progress["wrong_count"]
        else:
            new_box = 1  # Yanlış cevap - 1. kutuya döner
            new_correct = progress["correct_count"]
            new_wrong = progress["wrong_count"] + 1
        
        await db.student_progress.update_one(
            {"student_code": student_code, "word_id": word_id},
            {"$set": {
                "box_number": new_box,
                "last_studied_date": today,
                "correct_count": new_correct,
                "wrong_count": new_wrong
            }}
        )

# API Routes

@api_router.post("/auth/student/login")
async def student_login(request: LoginRequest):
    """Öğrenci giriş"""
    student = await db.students.find_one({"code": request.code})
    if not student:
        raise HTTPException(status_code=404, detail="Öğrenci bulunamadı")
    
    return {
        "success": True,
        "student": {
            "code": student["code"],
            "name": student["name"],
            "class_name": student["class_name"]
        }
    }

@api_router.post("/auth/admin/login")
async def admin_login(request: AdminLoginRequest):
    """Admin giriş"""
    if request.password != "admin123":
        raise HTTPException(status_code=401, detail="Yanlış şifre")
    
    return {"success": True, "message": "Admin girişi başarılı"}

@api_router.get("/student/{student_code}/next-word")
async def get_next_word(student_code: str):
    """Öğrenci için sonraki kelimeyi getir"""
    word = await get_next_word_for_student(student_code)
    if not word:
        return {"message": "Bugünlük çalışma tamamlandı!"}
    
    return {
        "word_id": word["word_id"],
        "english": word["english"],
        "box_number": word["box_number"]
    }

@api_router.post("/student/study")
async def submit_answer(session: StudySession):
    """Kelime cevabını değerlendir"""
    # Kelimeyi bul
    word = await db.words.find_one({"id": session.word_id})
    if not word:
        raise HTTPException(status_code=404, detail="Kelime bulunamadı")
    
    # Cevabı kontrol et
    is_correct = check_answer(session.answer, word["turkish"])
    
    # İlerlemeyi güncelle
    await update_word_progress(session.student_code, session.word_id, is_correct)
    
    # Doğru cevap ise hangi kutuya gittiğini hesapla
    progress = await db.student_progress.find_one({"student_code": session.student_code, "word_id": session.word_id})
    new_box = progress["box_number"] if progress else 1
    
    return {
        "is_correct": is_correct,
        "correct_answer": word["turkish"],
        "new_box": new_box if is_correct else 1,
        "message": f"Kelime {new_box}. kutuya geçti!" if is_correct else "Kelime 1. kutuya döndü."
    }

@api_router.get("/student/{student_code}/stats")
async def get_student_stats(student_code: str):
    """Öğrenci istatistikleri"""
    student = await db.students.find_one({"code": student_code})
    if not student:
        raise HTTPException(status_code=404, detail="Öğrenci bulunamadı")
    
    # Öğrencinin sınıfındaki toplam kelime sayısı
    total_words = await db.words.count_documents({"class_name": student["class_name"]})
    
    # Öğrencinin kelime ilerlemeleri
    progress_records = await db.student_progress.find({"student_code": student_code}).to_list(None)
    
    # Kutuları hesapla
    box_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    studied_today = 0
    today = get_today_date()
    
    # İlerleme kayıtlarından kutu sayılarını hesapla
    progress_word_ids = set()
    for progress in progress_records:
        box_counts[progress["box_number"]] += 1
        progress_word_ids.add(progress["word_id"])
        if progress["last_studied_date"] == today:
            studied_today += 1
    
    # İlerleme kaydı olmayan kelimeler 1. kutuda sayılır
    words_without_progress = total_words - len(progress_word_ids)
    box_counts[1] += words_without_progress
    
    return StudentStats(
        total_words=total_words,
        box1_words=box_counts[1],
        box2_words=box_counts[2],
        box3_words=box_counts[3],
        box4_words=box_counts[4],
        box5_words=box_counts[5],
        studied_today=studied_today
    )

@api_router.post("/admin/students/upload")
async def upload_students(file: UploadFile = File(...)):
    """CSV ile toplu öğrenci ekleme"""
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Sadece CSV dosyaları kabul edilir")
    
    content = await file.read()
    csv_content = content.decode("utf-8")
    csv_reader = csv.DictReader(io.StringIO(csv_content))
    
    added_count = 0
    for row in csv_reader:
        # Mevcut öğrenci kontrolü
        existing = await db.students.find_one({"code": row["code"]})
        if not existing:
            student = Student(
                code=row["code"],
                name=row["name"],
                class_name=row["class"]
            )
            await db.students.insert_one(student.dict())
            added_count += 1
    
    return {
        "message": f"{added_count} öğrenci başarıyla eklendi",
        "added_count": added_count
    }

@api_router.post("/admin/words/upload")
async def upload_words(file: UploadFile = File(...)):
    """CSV ile toplu kelime ekleme"""
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Sadece CSV dosyaları kabul edilir")
    
    content = await file.read()
    csv_content = content.decode("utf-8")
    csv_reader = csv.DictReader(io.StringIO(csv_content))
    
    added_count = 0
    for row in csv_reader:
        # Mevcut kelime kontrolü (aynı sınıf ve İngilizce kelime)
        existing = await db.words.find_one({
            "class_name": row["class"],
            "english": row["english"]
        })
        if not existing:
            word = Word(
                class_name=row["class"],
                english=row["english"],
                turkish=row["turkish"]
            )
            await db.words.insert_one(word.dict())
            added_count += 1
    
    return {
        "message": f"{added_count} kelime başarıyla eklendi",
        "added_count": added_count
    }

@api_router.get("/admin/students")
async def get_all_students():
    """Tüm öğrencileri listele"""
    students = await db.students.find().to_list(None)
    return [Student(**student) for student in students]

@api_router.get("/admin/words")
async def get_all_words():
    """Tüm kelimeleri listele"""
    words = await db.words.find().to_list(None)
    return [Word(**word) for word in words]

# Test endpoint
@api_router.get("/")
async def root():
    return {"message": "5 Kutu Yöntemi API"}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
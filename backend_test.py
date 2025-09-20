import requests
import sys
import json
import io
from datetime import datetime

class FiveBoxAPITester:
    def __init__(self, base_url="https://lingo-ladder.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.test_student_code = f"TEST{datetime.now().strftime('%H%M%S')}"
        
    def run_test(self, name, method, endpoint, expected_status, data=None, files=None):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}"
        headers = {}
        
        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers)
            elif method == 'POST':
                if files:
                    response = requests.post(url, files=files, headers=headers)
                else:
                    headers['Content-Type'] = 'application/json'
                    response = requests.post(url, json=data, headers=headers)
            
            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    print(f"   Response: {json.dumps(response_data, indent=2, ensure_ascii=False)}")
                    return True, response_data
                except:
                    return True, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Error: {json.dumps(error_data, indent=2, ensure_ascii=False)}")
                except:
                    print(f"   Error: {response.text}")
                return False, {}
                
        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_root_endpoint(self):
        """Test root API endpoint"""
        return self.run_test("Root API", "GET", "", 200)

    def test_student_login_invalid(self):
        """Test student login with invalid code"""
        return self.run_test(
            "Student Login (Invalid)",
            "POST", 
            "auth/student/login",
            404,
            data={"code": "INVALID_CODE"}
        )

    def test_admin_login_valid(self):
        """Test admin login with correct password"""
        return self.run_test(
            "Admin Login (Valid)",
            "POST",
            "auth/admin/login", 
            200,
            data={"password": "admin123"}
        )

    def test_admin_login_invalid(self):
        """Test admin login with wrong password"""
        return self.run_test(
            "Admin Login (Invalid)",
            "POST",
            "auth/admin/login",
            401,
            data={"password": "wrongpassword"}
        )

    def create_test_student(self):
        """Create test student via CSV upload"""
        print(f"\n📝 Creating test student with code: {self.test_student_code}")
        
        # Create CSV content for student
        csv_content = f"code,name,class\n{self.test_student_code},Test Student,5A"
        csv_file = io.StringIO(csv_content)
        
        files = {
            'file': ('students.csv', csv_content, 'text/csv')
        }
        
        success, response = self.run_test(
            "Upload Test Student",
            "POST",
            "admin/students/upload",
            200,
            files=files
        )
        return success

    def create_test_words(self):
        """Create test words via CSV upload"""
        print(f"\n📚 Creating test words for class 5A")
        
        # Create CSV content for words
        csv_content = """class,english,turkish
5A,hello,merhaba;selam
5A,world,dünya
5A,book,kitap
5A,water,su
5A,house,ev;konut"""
        
        files = {
            'file': ('words.csv', csv_content, 'text/csv')
        }
        
        success, response = self.run_test(
            "Upload Test Words",
            "POST",
            "admin/words/upload",
            200,
            files=files
        )
        return success

    def test_student_login_valid(self):
        """Test student login with valid code"""
        return self.run_test(
            "Student Login (Valid)",
            "POST",
            "auth/student/login",
            200,
            data={"code": self.test_student_code}
        )

    def test_student_stats(self):
        """Test student statistics"""
        return self.run_test(
            "Student Stats",
            "GET",
            f"student/{self.test_student_code}/stats",
            200
        )

    def test_next_word(self):
        """Test getting next word for student"""
        success, response = self.run_test(
            "Get Next Word",
            "GET",
            f"student/{self.test_student_code}/next-word",
            200
        )
        return success, response

    def test_study_session_correct(self, word_id):
        """Test submitting correct answer"""
        return self.run_test(
            "Study Session (Correct Answer)",
            "POST",
            "student/study",
            200,
            data={
                "student_code": self.test_student_code,
                "word_id": word_id,
                "answer": "merhaba"
            }
        )

    def test_study_session_wrong(self, word_id):
        """Test submitting wrong answer"""
        return self.run_test(
            "Study Session (Wrong Answer)",
            "POST",
            "student/study",
            200,
            data={
                "student_code": self.test_student_code,
                "word_id": word_id,
                "answer": "wrong_answer"
            }
        )

    def test_admin_endpoints(self):
        """Test admin list endpoints"""
        print(f"\n👥 Testing admin list endpoints...")
        
        success1, _ = self.run_test("List All Students", "GET", "admin/students", 200)
        success2, _ = self.run_test("List All Words", "GET", "admin/words", 200)
        
        return success1 and success2

def main():
    print("🚀 Starting 5 Kutu Yöntemi API Tests")
    print("=" * 50)
    
    tester = FiveBoxAPITester()
    
    # Test basic endpoints
    print("\n📡 Testing Basic Endpoints...")
    tester.test_root_endpoint()
    
    # Test authentication
    print("\n🔐 Testing Authentication...")
    tester.test_admin_login_valid()
    tester.test_admin_login_invalid()
    tester.test_student_login_invalid()
    
    # Create test data
    print("\n📊 Creating Test Data...")
    if not tester.create_test_student():
        print("❌ Failed to create test student, stopping tests")
        return 1
        
    if not tester.create_test_words():
        print("❌ Failed to create test words, stopping tests")
        return 1
    
    # Test with valid student
    print("\n👨‍🎓 Testing Student Features...")
    if not tester.test_student_login_valid()[0]:
        print("❌ Student login failed, stopping tests")
        return 1
    
    # Test student stats
    tester.test_student_stats()
    
    # Test word study system
    print("\n📚 Testing Word Study System...")
    success, next_word_response = tester.test_next_word()
    
    if success and 'word_id' in next_word_response:
        word_id = next_word_response['word_id']
        print(f"   Got word ID: {word_id}")
        
        # Test correct answer
        tester.test_study_session_correct(word_id)
        
        # Get next word again
        success2, next_word_response2 = tester.test_next_word()
        if success2 and 'word_id' in next_word_response2:
            word_id2 = next_word_response2['word_id']
            # Test wrong answer
            tester.test_study_session_wrong(word_id2)
    
    # Test admin endpoints
    tester.test_admin_endpoints()
    
    # Print final results
    print("\n" + "=" * 50)
    print(f"📊 Final Results: {tester.tests_passed}/{tester.tests_run} tests passed")
    
    if tester.tests_passed == tester.tests_run:
        print("🎉 All tests passed!")
        return 0
    else:
        print(f"⚠️  {tester.tests_run - tester.tests_passed} tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
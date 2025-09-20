import React, { useState, useEffect } from 'react';
import './App.css';
import { BrowserRouter, Routes, Route, Navigate, Link, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Toaster } from './components/ui/sonner';
import { toast } from 'sonner';
import { Button } from './components/ui/button';
import { Input } from './components/ui/input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './components/ui/card';
import { Badge } from './components/ui/badge';
import { Progress } from './components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './components/ui/tabs';
import { Upload, BookOpen, BarChart3, Users, FileText, LogOut, Home } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Auth Context
const AuthContext = React.createContext();

function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [isAdmin, setIsAdmin] = useState(false);

  useEffect(() => {
    const savedUser = localStorage.getItem('student');
    const savedAdmin = localStorage.getItem('isAdmin');
    if (savedUser) {
      setUser(JSON.parse(savedUser));
    }
    if (savedAdmin) {
      setIsAdmin(true);
    }
  }, []);

  const login = (userData) => {
    setUser(userData);
    localStorage.setItem('student', JSON.stringify(userData));
  };

  const adminLogin = () => {
    setIsAdmin(true);
    localStorage.setItem('isAdmin', 'true');
  };

  const logout = () => {
    setUser(null);
    setIsAdmin(false);
    localStorage.removeItem('student');
    localStorage.removeItem('isAdmin');
  };

  return (
    <AuthContext.Provider value={{ user, isAdmin, login, adminLogin, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

// Login Component
function Login() {
  const [code, setCode] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = React.useContext(AuthContext);

  const handleLogin = async (e) => {
    e.preventDefault();
    if (!code.trim()) {
      toast.error('Lütfen öğrenci kodunuzu girin');
      return;
    }

    setLoading(true);
    try {
      const response = await axios.post(`${API}/auth/student/login`, { code });
      login(response.data.student);
      toast.success(`Hoş geldin ${response.data.student.name}!`);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Giriş yapılamadı');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl font-bold text-indigo-800">📚 5 Kutu Yöntemi</CardTitle>
          <CardDescription>Kelime öğrenme uygulamasına hoş geldin!</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <Input
                type="text"
                placeholder="Öğrenci kodunuzu girin"
                value={code}
                onChange={(e) => setCode(e.target.value)}
                className="text-center text-lg"
              />
            </div>
            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? 'Giriş yapılıyor...' : 'Giriş Yap'}
            </Button>
          </form>
          <div className="mt-4 text-center">
            <a href="/admin" className="text-sm text-gray-500 hover:text-gray-700">
              Admin Paneli
            </a>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// Study Component
function Study() {
  const [currentWord, setCurrentWord] = useState(null);
  const [answer, setAnswer] = useState('');
  const [loading, setLoading] = useState(false);
  const [showResult, setShowResult] = useState(false);
  const [result, setResult] = useState(null);
  const { user } = React.useContext(AuthContext);

  const fetchNextWord = async () => {
    try {
      const response = await axios.get(`${API}/student/${user.code}/next-word`);
      if (response.data.message) {
        setCurrentWord(null);
        toast.success(response.data.message);
      } else {
        setCurrentWord(response.data);
      }
    } catch (error) {
      toast.error('Kelime yüklenirken hata oluştu');
    }
  };

  const submitAnswer = async (e) => {
    e.preventDefault();
    if (!answer.trim()) {
      toast.error('Lütfen cevabınızı girin');
      return;
    }

    setLoading(true);
    try {
      const response = await axios.post(`${API}/student/study`, {
        student_code: user.code,
        word_id: currentWord.word_id,
        answer: answer.trim()
      });

      setResult(response.data);
      setShowResult(true);
      setAnswer('');
    } catch (error) {
      toast.error('Cevap gönderilirken hata oluştu');
    } finally {
      setLoading(false);
    }
  };

  const nextWord = () => {
    setShowResult(false);
    setResult(null);
    fetchNextWord();
  };

  useEffect(() => {
    fetchNextWord();
  }, []);

  if (!currentWord && !showResult) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-green-50 to-emerald-100 flex items-center justify-center p-4">
        <Card className="w-full max-w-md text-center">
          <CardContent className="p-8">
            <div className="text-6xl mb-4">🎉</div>
            <h2 className="text-2xl font-bold text-green-800 mb-2">Tebrikler!</h2>
            <p className="text-green-600">Bugünlük çalışmanız tamamlandı.</p>
            <Button onClick={fetchNextWord} className="mt-4">
              Tekrar Kontrol Et
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (showResult) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-purple-50 to-pink-100 flex items-center justify-center p-4">
        <Card className="w-full max-w-md text-center">
          <CardContent className="p-8">
            <div className="text-6xl mb-4">
              {result.is_correct ? '✅' : '❌'}
            </div>
            <h2 className="text-2xl font-bold mb-2">
              {result.is_correct ? 'Doğru!' : 'Yanlış!'}
            </h2>
            <p className="text-gray-600 mb-2">
              Doğru cevap: <strong>{result.correct_answer}</strong>
            </p>
            <Badge variant={result.is_correct ? 'default' : 'destructive'} className="mb-4">
              {result.message}
            </Badge>
            <Button onClick={nextWord} className="w-full">
              Sonraki Kelime
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <CardTitle className="text-xl">
            Kelime Çalışması
          </CardTitle>
          <Badge variant="outline">
            {currentWord.box_number}. Kutu
          </Badge>
        </CardHeader>
        <CardContent>
          <div className="text-center mb-6">
            <div className="text-4xl font-bold text-indigo-800 mb-2">
              {currentWord.english}
            </div>
            <p className="text-gray-600">Bu kelimenin Türkçe anlamını yazın</p>
          </div>
          <form onSubmit={submitAnswer} className="space-y-4">
            <Input
              type="text"
              placeholder="Türkçe anlamını yazın..."
              value={answer}
              onChange={(e) => setAnswer(e.target.value)}
              className="text-center text-lg"
              autoFocus
            />
            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? 'Kontrol ediliyor...' : 'Cevabı Gönder'}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}

// Dashboard Component
function Dashboard() {
  const [stats, setStats] = useState(null);
  const { user, logout } = React.useContext(AuthContext);

  const fetchStats = async () => {
    try {
      const response = await axios.get(`${API}/student/${user.code}/stats`);
      setStats(response.data);
    } catch (error) {
      toast.error('İstatistikler yüklenirken hata oluştu');
    }
  };

  useEffect(() => {
    fetchStats();
  }, []);

  if (!stats) {
    return <div className="flex justify-center items-center min-h-screen">Yükleniyor...</div>;
  }

  const totalProgress = stats.total_words > 0 ? 
    ((stats.box2_words + stats.box3_words + stats.box4_words + stats.box5_words) / stats.total_words) * 100 : 0;

  return (
    <div className="min-h-screen bg-gradient-to-br from-emerald-50 to-teal-100 p-4">
      <div className="max-w-4xl mx-auto">
        <div className="mb-6 flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold text-teal-800">📊 Dashboard</h1>
            <p className="text-teal-600">Hoş geldin {user.name} ({user.class_name})</p>
          </div>
          <Button onClick={logout} variant="outline">
            <LogOut className="w-4 h-4 mr-2" />
            Çıkış
          </Button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
          <Card>
            <CardContent className="p-6 text-center">
              <div className="text-3xl font-bold text-blue-600">{stats.total_words}</div>
              <div className="text-gray-600">Toplam Kelime</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-6 text-center">
              <div className="text-3xl font-bold text-green-600">{stats.studied_today}</div>
              <div className="text-gray-600">Bugün Çalışılan</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-6 text-center">
              <div className="text-3xl font-bold text-purple-600">{totalProgress.toFixed(1)}%</div>
              <div className="text-gray-600">İlerleme</div>
            </CardContent>
          </Card>
        </div>

        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Kutulardaki Kelime Dağılımı</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {[1, 2, 3, 4, 5].map(box => (
                <div key={box} className="flex items-center justify-between">
                  <div className="flex items-center">
                    <Badge className="mr-3">{box}. Kutu</Badge>
                    <span>{stats[`box${box}_words`]} kelime</span>
                  </div>
                  <Progress 
                    value={stats.total_words > 0 ? (stats[`box${box}_words`] / stats.total_words) * 100 : 0} 
                    className="w-32" 
                  />
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <div className="flex gap-4">
          <Button asChild className="flex-1">
            <Link to="/study">
              <BookOpen className="w-4 h-4 mr-2" />
              Kelime Çalış
            </Link>
          </Button>
          <Button onClick={fetchStats} variant="outline">
            <BarChart3 className="w-4 h-4 mr-2" />
            Yenile
          </Button>
        </div>
      </div>
    </div>
  );
}

// Admin Login Component
function AdminLogin() {
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const { adminLogin } = React.useContext(AuthContext);

  const handleLogin = async (e) => {
    e.preventDefault();
    if (!password.trim()) {
      toast.error('Lütfen şifrenizi girin');
      return;
    }

    setLoading(true);
    try {
      await axios.post(`${API}/auth/admin/login`, { password });
      adminLogin();
      toast.success('Admin girişi başarılı!');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Yanlış şifre');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-red-50 to-pink-100 flex items-center justify-center p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl font-bold text-red-800">🔐 Admin Paneli</CardTitle>
          <CardDescription>Yönetici girişi</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleLogin} className="space-y-4">
            <Input
              type="password"
              placeholder="Admin şifresi"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="text-center"
            />
            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? 'Giriş yapılıyor...' : 'Giriş Yap'}
            </Button>
          </form>
          <div className="mt-4 text-center">
            <a href="/" className="text-sm text-gray-500 hover:text-gray-700">
              Ana Sayfaya Dön
            </a>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// Admin Panel Component
function AdminPanel() {
  const [studentsFile, setStudentsFile] = useState(null);
  const [wordsFile, setWordsFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const { logout } = React.useContext(AuthContext);

  const uploadStudents = async () => {
    if (!studentsFile) {
      toast.error('Lütfen bir CSV dosyası seçin');
      return;
    }

    setLoading(true);
    const formData = new FormData();
    formData.append('file', studentsFile);

    try {
      const response = await axios.post(`${API}/admin/students/upload`, formData);
      toast.success(response.data.message);
      setStudentsFile(null);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Yükleme başarısız');
    } finally {
      setLoading(false);
    }
  };

  const uploadWords = async () => {
    if (!wordsFile) {
      toast.error('Lütfen bir CSV dosyası seçin');
      return;
    }

    setLoading(true);
    const formData = new FormData();
    formData.append('file', wordsFile);

    try {
      const response = await axios.post(`${API}/admin/words/upload`, formData);
      toast.success(response.data.message);
      setWordsFile(null);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Yükleme başarısız');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-orange-50 to-red-100 p-4">
      <div className="max-w-4xl mx-auto">
        <div className="mb-6 flex justify-between items-center">
          <h1 className="text-3xl font-bold text-orange-800">⚙️ Admin Paneli</h1>
          <Button onClick={logout} variant="outline">
            <LogOut className="w-4 h-4 mr-2" />
            Çıkış
          </Button>
        </div>

        <Tabs defaultValue="upload" className="space-y-6">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="upload">Dosya Yükleme</TabsTrigger>
            <TabsTrigger value="manage">Yönetim</TabsTrigger>
          </TabsList>

          <TabsContent value="upload" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center">
                  <Users className="w-5 h-5 mr-2" />
                  Öğrenci Yükleme
                </CardTitle>
                <CardDescription>
                  CSV formatı: code,name,class
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <Input
                  type="file"
                  accept=".csv"
                  onChange={(e) => setStudentsFile(e.target.files[0])}
                />
                <Button 
                  onClick={uploadStudents} 
                  disabled={loading || !studentsFile}
                  className="w-full"
                >
                  <Upload className="w-4 h-4 mr-2" />
                  Öğrencileri Yükle
                </Button>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center">
                  <FileText className="w-5 h-5 mr-2" />
                  Kelime Yükleme
                </CardTitle>
                <CardDescription>
                  CSV formatı: class,english,turkish
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <Input
                  type="file"
                  accept=".csv"
                  onChange={(e) => setWordsFile(e.target.files[0])}
                />
                <Button 
                  onClick={uploadWords} 
                  disabled={loading || !wordsFile}
                  className="w-full"
                >
                  <Upload className="w-4 h-4 mr-2" />
                  Kelimeleri Yükle
                </Button>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="manage">
            <Card>
              <CardContent className="p-6 text-center">
                <p className="text-gray-600">Yönetim özellikleri yakında eklenecek...</p>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}

// Main App Component
function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <div className="App">
          <Routes>
            <Route path="/" element={<AppRouter />} />
            <Route path="/study" element={<ProtectedRoute><Study /></ProtectedRoute>} />
            <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
            <Route path="/admin" element={<AdminRouter />} />
            <Route path="/admin/panel" element={<AdminProtectedRoute><AdminPanel /></AdminProtectedRoute>} />
          </Routes>
          <Toaster />
        </div>
      </BrowserRouter>
    </AuthProvider>
  );
}

function AppRouter() {
  const { user } = React.useContext(AuthContext);
  return user ? <Navigate to="/dashboard" /> : <Login />;
}

function AdminRouter() {
  const { isAdmin } = React.useContext(AuthContext);
  return isAdmin ? <Navigate to="/admin/panel" /> : <AdminLogin />;
}

function ProtectedRoute({ children }) {
  const { user } = React.useContext(AuthContext);
  return user ? children : <Navigate to="/" />;
}

function AdminProtectedRoute({ children }) {
  const { isAdmin } = React.useContext(AuthContext);
  return isAdmin ? children : <Navigate to="/admin" />;
}

export default App;
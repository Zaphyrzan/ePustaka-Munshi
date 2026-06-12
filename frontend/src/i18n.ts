import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'

// Mirrors the bilingual EN/BM support of the Flask templates.
// Keys grow as pages are migrated; missing keys fall back to English text.
const resources = {
  en: {
    translation: {
      appName: 'ePustaka Munshi',
      login: 'Login',
      logout: 'Logout',
      username: 'Username / Member ID',
      password: 'Password',
      dashboard: 'Dashboard',
      catalog: 'Catalog',
      circulation: 'Circulation',
      ocr: 'OCR Digitization',
      users: 'Users',
      students: 'Students',
      search: 'Search',
      searchPlaceholder: 'Search title, author or ISBN...',
      title: 'Title',
      author: 'Author',
      publisher: 'Publisher',
      year: 'Year',
      category: 'Category',
      copies: 'Copies',
      available: 'Available',
      checkout: 'Checkout',
      return: 'Return',
      overdue: 'Overdue',
      activeLoans: 'Active Loans',
      loading: 'Loading...',
      error: 'Something went wrong',
      welcomeBack: 'Welcome back',
      invalidLogin: 'Invalid username or password',
    },
  },
  ms: {
    translation: {
      appName: 'ePustaka Munshi',
      login: 'Log Masuk',
      logout: 'Log Keluar',
      username: 'Nama Pengguna / ID Ahli',
      password: 'Kata Laluan',
      dashboard: 'Papan Pemuka',
      catalog: 'Katalog',
      circulation: 'Peredaran',
      ocr: 'Pendigitalan OCR',
      users: 'Pengguna',
      students: 'Pelajar',
      search: 'Cari',
      searchPlaceholder: 'Cari tajuk, pengarang atau ISBN...',
      title: 'Tajuk',
      author: 'Pengarang',
      publisher: 'Penerbit',
      year: 'Tahun',
      category: 'Kategori',
      copies: 'Naskhah',
      available: 'Tersedia',
      checkout: 'Pinjaman',
      return: 'Pemulangan',
      overdue: 'Lewat Tempoh',
      activeLoans: 'Pinjaman Aktif',
      loading: 'Memuatkan...',
      error: 'Berlaku ralat',
      welcomeBack: 'Selamat kembali',
      invalidLogin: 'Nama pengguna atau kata laluan salah',
    },
  },
}

i18n.use(initReactI18next).init({
  resources,
  lng: localStorage.getItem('lang') || 'en',
  fallbackLng: 'en',
  interpolation: { escapeValue: false },
})

export function setLanguage(lang: 'en' | 'ms') {
  localStorage.setItem('lang', lang)
  i18n.changeLanguage(lang)
}

export default i18n

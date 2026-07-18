import axios from "axios";

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL?.trim() || "http://localhost:8000";

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
});

api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("studymate_token");

    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    return config;
  },
  (error) => Promise.reject(error),
);

export function errorMessage(error) {
  const response = error?.response;
  const detail = response?.data?.detail;

  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        const field = Array.isArray(item?.loc)
          ? item.loc.filter((part) => part !== "body").join(".")
          : "";

        const message = item?.msg || "Geçersiz bilgi";

        return field ? `${field}: ${message}` : message;
      })
      .join(" · ");
  }

  if (typeof detail === "string" && detail.trim()) {
    return detail;
  }

  if (detail && typeof detail === "object") {
    return detail.message || "İstek işlenirken bir hata oluştu.";
  }

  if (error?.code === "ECONNABORTED") {
    return "İstek zaman aşımına uğradı. Lütfen tekrar deneyin.";
  }

  if (!response && error?.request) {
    return "Sunucuya ulaşılamıyor. Backend servisinin çalıştığını kontrol edin.";
  }

  if (response?.status === 400) {
    return "Gönderilen bilgiler geçersiz.";
  }

  if (response?.status === 401) {
    return "Oturum süreniz dolmuş veya giriş bilgileriniz geçersiz.";
  }

  if (response?.status === 403) {
    return "Bu işlem için yetkiniz bulunmuyor.";
  }

  if (response?.status === 404) {
    return "İstenen kaynak bulunamadı.";
  }

  if (response?.status === 409) {
    return "Bu kayıt zaten mevcut.";
  }

  if (response?.status === 422) {
    return "Gönderilen alanları kontrol edin.";
  }

  if (response?.status >= 500) {
    return "Sunucu tarafında bir hata oluştu. Lütfen daha sonra tekrar deneyin.";
  }

  return error?.message || "Beklenmeyen bir hata oluştu.";
}

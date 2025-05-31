"use client";

export default function Home() {
  const handleLogin = () => {
    const baseUrl = process.env.NEXT_PUBLIC_API_URL;
    if (!baseUrl) {
      alert("API URL이 설정되지 않았습니다.");
      return;
    }

    const loginUrl = `${baseUrl}/api/auth/kakao/login`;
    window.location.href = loginUrl;
  };

  return (
    <main className="flex h-screen items-center justify-center">
      <button
        onClick={handleLogin}
        className="px-4 py-2 bg-yellow-400 rounded text-black font-semibold"
      >
        카카오 로그인
      </button>
    </main>
  );
}

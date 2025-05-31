"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

export default function KakaoCallbackPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [status, setStatus] = useState("🔄 로그인 처리 중입니다...");

  useEffect(() => {
    const code = searchParams.get("code");

    const handleKakaoCallback = async () => {
      if (!code) {
        setStatus("❌ 인가 코드가 없습니다.");
        return;
      }

      try {
        const res = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL}/api/auth/kakao/callback?code=${code}`
        );

        const data = await res.json();

        if (!res.ok) {
          console.error("❌ 로그인 실패:", data);
          setStatus("❌ 로그인 실패");
          alert(`로그인 실패: ${data.detail || "서버 오류"}`);
          router.push("/");
          return;
        }

        if (data.access_token) {
          localStorage.setItem("access_token", data.access_token);
          localStorage.setItem("user_id", data.user_id);
          localStorage.setItem("nickname", data.nickname);
          console.log("✅ 로그인 성공:", data);
          router.push("/onboarding"); // or "/" if onboarding is done
        } else {
          console.warn("⚠️ 응답에 토큰 없음:", data);
          setStatus("❌ 로그인 실패");
          alert("로그인 실패: 응답에 access_token 없음");
          router.push("/");
        }
      } catch (err) {
        console.error("🚨 로그인 처리 중 예외:", err);
        setStatus("❌ 로그인 중 오류 발생");
        alert("로그인 처리 중 예외 발생");
        router.push("/");
      }
    };

    handleKakaoCallback();
  }, [searchParams, router]);

  return (
    <div className="flex h-screen items-center justify-center text-lg font-semibold">
      {status}
    </div>
  );
}

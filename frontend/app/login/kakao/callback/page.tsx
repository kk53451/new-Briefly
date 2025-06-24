"use client"

import { useEffect, useState, useRef } from "react"
import { useRouter, useSearchParams } from "next/navigation"

const API_BASE_URL = "http://localhost:8000"

export default function KakaoCallbackPage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [status, setStatus] = useState("로그인 처리 중입니다...")
  const processingRef = useRef(false) // useRefでより強力な重複防止

  useEffect(() => {
    if (processingRef.current) return // すでに処理中なら中断
    
    const code = searchParams.get("code")
    const error = searchParams.get("error")

    const handleKakaoCallback = async () => {
      processingRef.current = true // 処理開始フラグ
      
      // カカオからエラーが返された場合
      if (error) {
        setStatus("카카오 로그인이 취소되었습니다.")
        setTimeout(() => router.push("/"), 3000)
        return
      }

      if (!code) {
        setStatus("인가 코드가 없습니다.")
        setTimeout(() => router.push("/"), 2000)
        return
      }

      try {
        setStatus("서버와 통신 중...")
        // 認証コード受信確認

        // URLを整理してコード再利用防止
        const currentUrl = window.location.href
        const urlWithoutParams = window.location.origin + window.location.pathname
        if (currentUrl !== urlWithoutParams) {
          window.history.replaceState({}, document.title, urlWithoutParams)
          // URLパラメータ削除完了
        }

        const res = await fetch(`${API_BASE_URL}/api/auth/kakao/callback?code=${encodeURIComponent(code)}`, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
        })

        const data = await res.json()

        if (!res.ok) {
          console.error("로그인 실패:", data)
          setStatus("로그인 실패")
          
          // 特定エラーメッセージ処理
          if (data.detail && (
            data.detail.includes("만료되었거나 이미 사용") || 
            data.detail.includes("이미 사용된 코드")
          )) {
            alert("인증 코드가 만료되었거나 이미 사용되었습니다. 다시 로그인해주세요.")
            router.push("/")
          } else {
            alert(`로그인 실패: ${data.detail || "서버 오류"}`)
            setTimeout(() => router.push("/"), 2000)
          }
          return
        }

        if (data.access_token) {
          // トークンとユーザー情報を保存
          localStorage.setItem("access_token", data.access_token)
          localStorage.setItem("user_id", data.user_id)
          localStorage.setItem("nickname", data.nickname)

          setStatus("로그인 성공! 리디렉션 중...")

          // オンボーディング状態確認
          try {
            const onboardingRes = await fetch(`${API_BASE_URL}/api/user/onboarding/status`, {
              headers: {
                Authorization: `Bearer ${data.access_token}`,
              },
            })

            if (onboardingRes.ok) {
              const onboardingData = await onboardingRes.json()

              if (onboardingData.onboarded) {
                router.push("/ranking")
              } else {
                router.push("/onboarding")
              }
            } else {
              // オンボーディング状態確認失敗時はデフォルトでオンボーディングへ
              router.push("/onboarding")
            }
                      } catch (onboardingError) {
              // オンボーディング状態確認失敗時はデフォルトでオンボーディングへ
              router.push("/onboarding")
            }
                  } else {
            setStatus("로그인 실패")
          alert("로그인 실패: 응답에 access_token 없음")
          setTimeout(() => router.push("/"), 2000)
        }
              } catch (err) {
          setStatus("로그인 중 오류 발생")
          alert("로그인 처리 중 예외 발생")
          setTimeout(() => router.push("/"), 2000)
        }
    }

    handleKakaoCallback()
  }, [searchParams, router])

  return (
    <div className="flex h-screen items-center justify-center">
      <div className="text-center">
        <div className="text-lg font-semibold mb-4">{status}</div>
        {status.includes("처리 중") && (
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
        )}
        {status.includes("실패") && (
          <div className="mt-4">
            <button 
              onClick={() => router.push("/")}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
            >
              홈으로 돌아가기
            </button>
          </div>
        )}
        <div className="mt-4 text-sm text-gray-600">
          ページをリロードしないでください
        </div>
      </div>
    </div>
  )
}

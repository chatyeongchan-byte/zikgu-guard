"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";

export default function Home() {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [height, setHeight] = useState("");
  const [weight, setWeight] = useState("");
  const [saved, setSaved] = useState(false);
  const router = useRouter();

  useEffect(() => {
    setHeight(localStorage.getItem("zg_height") ?? "");
    setWeight(localStorage.getItem("zg_weight") ?? "");
  }, []);

  const handleSave = () => {
    localStorage.setItem("zg_height", height);
    localStorage.setItem("zg_weight", weight);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!url.trim()) return;
    setLoading(true);
    router.push(`/result?url=${encodeURIComponent(url)}`);
  };

  return (
    <main className="min-h-screen bg-white flex flex-col items-center justify-center px-4">

      {/* 로고 */}
      <div className="mb-10 text-center">
        <h1 className="text-4xl font-bold text-gray-900 tracking-tight mb-2">직구가드</h1>
        <p className="text-gray-500 text-base">실패를 없애다</p>
      </div>

      {/* URL 검색창 */}
      <form onSubmit={handleSubmit} className="w-full max-w-xl">
        <div className="flex items-center border border-gray-200 rounded-full px-5 py-3 shadow-sm hover:shadow-md transition-shadow bg-white gap-3">
          <svg className="w-5 h-5 text-gray-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            type="text"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="타오바오 / 웨이디안 URL을 붙여넣으세요"
            className="flex-1 outline-none text-gray-800 text-sm placeholder-gray-400 bg-transparent"
          />
          {url && (
            <button type="button" onClick={() => setUrl("")} className="text-gray-400 hover:text-gray-600 flex-shrink-0">✕</button>
          )}
        </div>

        {/* 내 정보 입력 (URL 바로 아래) */}
        <div className="flex items-center gap-2 mt-3 px-1">
          <span className="text-xs text-gray-400 flex-shrink-0">내 정보</span>
          <div className="flex items-center border border-gray-200 rounded-lg px-3 py-1.5 gap-1.5 bg-white">
            <input
              type="number"
              value={height}
              onChange={(e) => setHeight(e.target.value)}
              placeholder="키 cm"
              className="w-16 outline-none text-sm text-gray-700 placeholder-gray-300 bg-transparent"
            />
          </div>
          <div className="flex items-center border border-gray-200 rounded-lg px-3 py-1.5 gap-1.5 bg-white">
            <input
              type="number"
              value={weight}
              onChange={(e) => setWeight(e.target.value)}
              placeholder="몸무게 kg"
              className="w-20 outline-none text-sm text-gray-700 placeholder-gray-300 bg-transparent"
            />
          </div>
          <button
            type="button"
            onClick={handleSave}
            className="text-xs px-3 py-1.5 bg-gray-100 hover:bg-gray-200 text-gray-600 rounded-lg transition-colors flex-shrink-0"
          >
            {saved ? "저장됨 ✓" : "저장"}
          </button>
        </div>

        <div className="flex justify-center gap-3 mt-5">
          <button
            type="submit"
            disabled={!url.trim() || loading}
            className="px-5 py-2 text-sm bg-gray-100 hover:bg-gray-200 text-gray-800 rounded-md transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {loading ? "분석 중..." : "셀러 검증"}
          </button>
          <button
            type="button"
            onClick={() => setUrl("")}
            className="px-5 py-2 text-sm bg-gray-100 hover:bg-gray-200 text-gray-800 rounded-md transition-colors"
          >
            초기화
          </button>
        </div>
      </form>

      {loading && (
        <div className="mt-12 flex flex-col items-center gap-3 text-gray-400">
          <div className="w-6 h-6 border-2 border-gray-200 border-t-gray-500 rounded-full animate-spin" />
          <p className="text-sm">분석 중입니다...</p>
        </div>
      )}

      <p className="absolute bottom-6 text-xs text-gray-300">타오바오 · 웨이디안 셀러 신뢰도 분석</p>
    </main>
  );
}

"use client";

import { useState, useEffect } from "react";
import Link from "next/link";

export default function SettingsPage() {
  const [height, setHeight] = useState("");
  const [weight, setWeight] = useState("");
  const [saved, setSaved] = useState(false);

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

  return (
    <main className="min-h-screen bg-white flex flex-col items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="flex items-center gap-3 mb-8">
          <Link href="/" className="text-gray-400 hover:text-gray-600 text-sm">← 돌아가기</Link>
        </div>

        <h1 className="text-2xl font-bold text-gray-900 mb-1">내 정보</h1>
        <p className="text-sm text-gray-400 mb-8">사이즈 추천에 사용됩니다</p>

        <div className="space-y-4">
          <div>
            <label className="text-xs text-gray-400 mb-1.5 block">키 (cm)</label>
            <input
              type="number"
              value={height}
              onChange={(e) => setHeight(e.target.value)}
              placeholder="예: 175"
              className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm text-gray-800 outline-none focus:border-gray-400 transition-colors"
            />
          </div>
          <div>
            <label className="text-xs text-gray-400 mb-1.5 block">몸무게 (kg)</label>
            <input
              type="number"
              value={weight}
              onChange={(e) => setWeight(e.target.value)}
              placeholder="예: 70"
              className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm text-gray-800 outline-none focus:border-gray-400 transition-colors"
            />
          </div>

          <button
            onClick={handleSave}
            className="w-full py-3 bg-gray-900 hover:bg-gray-700 text-white text-sm rounded-xl transition-colors mt-2"
          >
            {saved ? "저장됐습니다 ✓" : "저장"}
          </button>
        </div>
      </div>
    </main>
  );
}

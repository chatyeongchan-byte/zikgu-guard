"use client";

import { useSearchParams } from "next/navigation";
import { Suspense } from "react";
import Link from "next/link";

// 더미 데이터 (API 연동 전)
const dummyResult = {
  sellerName: "潮流范儿旗舰店",
  platform: "타오바오",
  score: 74,
  grade: "B",
  reviews: { positive: 82, negative: 18, total: 1243 },
  operatingYears: "2년 3개월",
  fakeReview: false,
  reportCount: 0,
  summary: "전반적으로 긍정적인 리뷰가 많으며, 배송 지연 관련 불만이 일부 있습니다. 판매 이력이 안정적이고 신고 이력이 없어 신뢰할 수 있는 셀러입니다.",
  warnings: [] as string[],
};

function gradeColor(grade: string) {
  const map: Record<string, string> = {
    A: "text-emerald-600",
    B: "text-blue-600",
    C: "text-yellow-600",
    D: "text-orange-600",
    F: "text-red-600",
  };
  return map[grade] ?? "text-gray-600";
}

function ScoreRing({ score }: { score: number }) {
  const r = 40;
  const circ = 2 * Math.PI * r;
  const filled = (score / 100) * circ;
  return (
    <svg width="100" height="100" viewBox="0 0 100 100">
      <circle cx="50" cy="50" r={r} fill="none" stroke="#f3f4f6" strokeWidth="10" />
      <circle
        cx="50" cy="50" r={r} fill="none"
        stroke={score >= 80 ? "#10b981" : score >= 60 ? "#3b82f6" : score >= 40 ? "#f59e0b" : "#ef4444"}
        strokeWidth="10"
        strokeDasharray={`${filled} ${circ}`}
        strokeLinecap="round"
        transform="rotate(-90 50 50)"
      />
      <text x="50" y="55" textAnchor="middle" fontSize="18" fontWeight="bold" fill="#111">
        {score}
      </text>
    </svg>
  );
}

function ResultContent() {
  const params = useSearchParams();
  const url = params.get("url") ?? "";
  const r = dummyResult;

  return (
    <main className="min-h-screen bg-white px-4 py-10 max-w-xl mx-auto">
      {/* 헤더 */}
      <div className="flex items-center justify-between mb-8">
        <Link href="/" className="text-xl font-bold text-gray-900 tracking-tight">
          직구가드
        </Link>
        <span className="text-xs text-gray-400 truncate max-w-[200px]">{url}</span>
      </div>

      {/* 점수 카드 */}
      <div className="border border-gray-100 rounded-2xl p-6 shadow-sm mb-4">
        <div className="flex items-center gap-6">
          <ScoreRing score={r.score} />
          <div>
            <p className="text-sm text-gray-400 mb-1">신뢰 점수</p>
            <div className="flex items-baseline gap-2">
              <span className={`text-5xl font-bold ${gradeColor(r.grade)}`}>{r.grade}</span>
              <span className="text-gray-400 text-sm">등급</span>
            </div>
            <p className="text-xs text-gray-400 mt-1">{r.sellerName} · {r.platform}</p>
          </div>
        </div>
      </div>

      {/* 요약 */}
      <div className="border border-gray-100 rounded-2xl p-5 shadow-sm mb-4">
        <p className="text-xs text-gray-400 mb-2 font-medium uppercase tracking-wide">AI 요약</p>
        <p className="text-sm text-gray-700 leading-relaxed">{r.summary}</p>
      </div>

      {/* 세부 지표 */}
      <div className="border border-gray-100 rounded-2xl p-5 shadow-sm mb-4 space-y-3">
        <p className="text-xs text-gray-400 font-medium uppercase tracking-wide mb-1">세부 분석</p>

        <div className="flex justify-between items-center">
          <span className="text-sm text-gray-600">리뷰 긍정률</span>
          <div className="flex items-center gap-2">
            <div className="w-24 h-1.5 bg-gray-100 rounded-full overflow-hidden">
              <div className="h-full bg-emerald-400 rounded-full" style={{ width: `${r.reviews.positive}%` }} />
            </div>
            <span className="text-sm font-medium text-gray-800">{r.reviews.positive}%</span>
          </div>
        </div>

        <div className="flex justify-between items-center">
          <span className="text-sm text-gray-600">운영 기간</span>
          <span className="text-sm font-medium text-gray-800">{r.operatingYears}</span>
        </div>

        <div className="flex justify-between items-center">
          <span className="text-sm text-gray-600">가짜 리뷰</span>
          <span className={`text-sm font-medium ${r.fakeReview ? "text-red-500" : "text-emerald-600"}`}>
            {r.fakeReview ? "의심 패턴 발견" : "없음"}
          </span>
        </div>

        <div className="flex justify-between items-center">
          <span className="text-sm text-gray-600">사기 신고</span>
          <span className={`text-sm font-medium ${r.reportCount > 0 ? "text-red-500" : "text-emerald-600"}`}>
            {r.reportCount > 0 ? `${r.reportCount}건` : "없음"}
          </span>
        </div>

        <div className="flex justify-between items-center">
          <span className="text-sm text-gray-600">총 리뷰 수</span>
          <span className="text-sm font-medium text-gray-800">{r.reviews.total.toLocaleString()}개</span>
        </div>
      </div>

      {/* 경고 */}
      {r.warnings.length > 0 && (
        <div className="border border-red-100 bg-red-50 rounded-2xl p-5 mb-4">
          <p className="text-xs text-red-400 font-medium uppercase tracking-wide mb-2">주의사항</p>
          {r.warnings.map((w, i) => (
            <p key={i} className="text-sm text-red-600">⚠ {w}</p>
          ))}
        </div>
      )}

      {/* 다시 검색 */}
      <div className="flex justify-center mt-6">
        <Link
          href="/"
          className="px-5 py-2 text-sm bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-md transition-colors"
        >
          다른 셀러 검증하기
        </Link>
      </div>
    </main>
  );
}

export default function ResultPage() {
  return (
    <Suspense>
      <ResultContent />
    </Suspense>
  );
}

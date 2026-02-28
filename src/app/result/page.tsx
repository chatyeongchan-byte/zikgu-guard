"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import Link from "next/link";

type AnalyzeResult = {
  sellerName: string;
  platform: string;
  sellerScore: number;
  sellerGrade: string;
  productScore: number;
  productGrade: string;
  reviews: { positive: number; negative: number; total: number };
  operatingYears: string;
  fakeReview: boolean;
  reportCount: number;
  summary: string;
  warnings: string[];
  raw?: { productTitle?: string; price?: string; salesCount?: string };
  sizeImages?: string[];
  seller?: {
    id: string;
    grade: string;
    reorderRate: string;
    totalSales: string;
    shopScore: string;
    followers: string;
    location: string;
    lastLogin: string;
  };
  aiSummary?: string;
  mainImage?: string;
  sizeChart?: {
    tables: { label: string; headers: string[]; rows: string[][] }[];
  } | null;
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
  const [result, setResult] = useState<AnalyzeResult | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!url) return;
    const height = localStorage.getItem("zg_height") ?? "";
    const weight = localStorage.getItem("zg_weight") ?? "";
    fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url, height, weight }),
    })
      .then((res) => res.json())
      .then(setResult)
      .catch(() => setError("분석 중 오류가 발생했습니다."));
  }, [url]);

  if (error) {
    return (
      <main className="min-h-screen bg-white flex flex-col items-center justify-center gap-4">
        <p className="text-red-500 text-sm">{error}</p>
        <Link href="/" className="text-sm text-gray-500 underline">돌아가기</Link>
      </main>
    );
  }

  if (!result) {
    return (
      <main className="min-h-screen bg-white flex flex-col items-center justify-center gap-3 text-gray-400">
        <div className="w-6 h-6 border-2 border-gray-200 border-t-gray-500 rounded-full animate-spin" />
        <p className="text-sm">셀러 정보를 분석하고 있습니다...</p>
      </main>
    );
  }

  const r = result;

  return (
    <main className="min-h-screen bg-white px-4 py-10 max-w-xl mx-auto">
      {/* 헤더 */}
      <div className="flex items-center justify-between mb-8">
        <Link href="/" className="text-xl font-bold text-gray-900 tracking-tight">
          직구가드
        </Link>
        <span className="text-xs text-gray-400 truncate max-w-[200px]">{url}</span>
      </div>

      {/* 점수 카드 — 셀러 + 상품 */}
      <div className="grid grid-cols-2 gap-3 mb-4">
        <div className="border border-gray-100 rounded-2xl p-5 shadow-sm flex flex-col items-center gap-2">
          <p className="text-xs text-gray-400 font-medium">셀러 신뢰도</p>
          <ScoreRing score={r.sellerScore} />
          <span className={`text-2xl font-bold ${gradeColor(r.sellerGrade)}`}>{r.sellerGrade}</span>
          <p className="text-[11px] text-gray-400 text-center">
            <span className="text-gray-300">{r.platform} · </span>{r.sellerName}
          </p>
        </div>
        <div className="border border-gray-100 rounded-2xl p-5 shadow-sm flex flex-col items-center gap-2">
          <p className="text-xs text-gray-400 font-medium">상품 점수</p>
          <ScoreRing score={r.productScore} />
          <span className={`text-2xl font-bold ${gradeColor(r.productGrade)}`}>{r.productGrade}</span>
          {r.raw?.salesCount && r.raw.salesCount !== "정보 없음" ? (
            <p className="text-[11px] text-gray-400">판매 {Number(r.raw.salesCount).toLocaleString()}건</p>
          ) : (
            <p className="text-[11px] text-gray-400">{r.platform}</p>
          )}
        </div>
      </div>

      {/* 셀러 정보 */}
      {r.seller && (
        <div className="border border-gray-100 rounded-2xl p-5 shadow-sm mb-4 space-y-3">
          <p className="text-xs text-gray-400 font-medium uppercase tracking-wide mb-1">셀러 정보</p>

          {r.seller.id !== "정보 없음" && (
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">셀러 ID</span>
              <span className="text-sm font-medium text-gray-800">{r.seller.id}</span>
            </div>
          )}
          {r.seller.grade !== "정보 없음" && (
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">등급</span>
              <span className="text-sm font-medium text-gray-800">{r.seller.grade}</span>
            </div>
          )}
          {r.seller.reorderRate !== "정보 없음" && (
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">재주문율</span>
              <span className="text-sm font-semibold text-blue-600">{r.seller.reorderRate}</span>
            </div>
          )}
          {r.seller.shopScore !== "정보 없음" && (
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">샵 점수</span>
              <span className="text-sm font-medium text-gray-800">{r.seller.shopScore}</span>
            </div>
          )}
          {r.seller.totalSales !== "정보 없음" && (
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">누적 판매</span>
              <span className="text-sm font-medium text-gray-800">{r.seller.totalSales}건</span>
            </div>
          )}
          {r.seller.followers !== "정보 없음" && (
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">팔로워</span>
              <span className="text-sm font-medium text-gray-800">{Number(r.seller.followers).toLocaleString()}명</span>
            </div>
          )}
          {r.seller.location !== "정보 없음" && (
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">소재지</span>
              <span className="text-sm font-medium text-gray-800">{r.seller.location}</span>
            </div>
          )}
          {r.seller.lastLogin !== "정보 없음" && (
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">마지막 접속</span>
              <span className="text-sm font-medium text-gray-800">{r.seller.lastLogin}</span>
            </div>
          )}
        </div>
      )}

      {/* 대표 이미지 */}
      {r.mainImage && (
        <div className="mb-4 rounded-2xl overflow-hidden border border-gray-100 shadow-sm">
          <img
            src={r.mainImage}
            alt="상품 이미지"
            className="w-full object-cover max-h-72"
          />
        </div>
      )}

      {/* AI 요약 */}
      <div className="border border-gray-100 rounded-2xl p-5 shadow-sm mb-4">
        <p className="text-xs text-gray-400 mb-2 font-medium uppercase tracking-wide">AI 분석</p>
        {r.aiSummary ? (
          <p className="text-sm text-gray-700 leading-relaxed whitespace-pre-line">{r.aiSummary}</p>
        ) : (
          <p className="text-sm text-gray-700 leading-relaxed">{r.summary}</p>
        )}
      </div>

      {/* 사이즈표 */}
      {!r.sizeChart?.tables?.length && !r.sizeImages?.length && (
        <div className="border border-gray-100 rounded-2xl p-5 shadow-sm mb-4">
          <p className="text-xs text-gray-400 font-medium uppercase tracking-wide mb-2">사이즈표</p>
          <p className="text-sm text-gray-400">사이즈 정보가 없습니다.</p>
        </div>
      )}
      {/* 파싱된 사이즈표 없지만 이미지는 있을 때 — 원본 이미지 표시 */}
      {!r.sizeChart?.tables?.length && r.sizeImages && r.sizeImages.length > 0 && (
        <div className="border border-gray-100 rounded-2xl p-5 shadow-sm mb-4">
          <p className="text-xs text-gray-400 font-medium uppercase tracking-wide mb-3">사이즈표</p>
          <div className="space-y-3">
            {r.sizeImages.map((imgUrl, i) => (
              <img key={i} src={imgUrl} alt="사이즈표" className="w-full rounded-lg" />
            ))}
          </div>
        </div>
      )}
      {r.sizeChart?.tables && r.sizeChart.tables.length > 0 && (
        <div className="border border-gray-100 rounded-2xl p-5 shadow-sm mb-4">
          <p className="text-xs text-gray-400 font-medium uppercase tracking-wide mb-4">사이즈표</p>
          <div className="space-y-5">
            {r.sizeChart.tables.map((table, ti) => (
              <div key={ti}>
                {r.sizeChart!.tables.length > 1 && (
                  <p className="text-xs font-semibold text-gray-500 mb-2 px-1">
                    {table.label === "상의" ? "👕 상의" : table.label === "하의" ? "👖 하의" : table.label}
                  </p>
                )}
                <div className="overflow-x-auto">
                  <table className="w-full text-sm border-collapse">
                    <thead>
                      <tr>
                        {table.headers.map((h, i) => (
                          <th key={i} className="text-left text-xs text-gray-400 font-medium pb-2 pr-4 border-b border-gray-100 whitespace-nowrap">
                            {h}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {table.rows.map((row, i) => (
                        <tr key={i} className={i % 2 === 1 ? "bg-gray-50" : ""}>
                          {row.map((cell, j) => (
                            <td key={j} className={`py-2 pr-4 text-sm whitespace-nowrap ${j === 0 ? "font-semibold text-gray-900" : "text-gray-600"}`}>
                              {cell}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 상품 정보 (세부 분석) */}
      {r.raw && (r.raw.productTitle || r.raw.price) && (
        <div className="border border-gray-100 rounded-2xl p-5 shadow-sm mb-4 space-y-3">
          <p className="text-xs text-gray-400 font-medium uppercase tracking-wide mb-1">상품 정보</p>

          {r.raw.productTitle && r.raw.productTitle !== "정보 없음" && (
            <div className="flex justify-between items-start gap-4">
              <span className="text-sm text-gray-600 flex-shrink-0">상품명</span>
              <span className="text-sm font-medium text-gray-800 text-right">{r.raw.productTitle}</span>
            </div>
          )}

          {r.raw.price && r.raw.price !== "정보 없음" && (
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">가격</span>
              <span className="text-base font-semibold text-gray-900">{r.raw.price}</span>
            </div>
          )}

          {r.reviews.total > 0 && (
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">리뷰 수</span>
              <span className="text-sm font-medium text-gray-800">{r.reviews.total.toLocaleString()}개</span>
            </div>
          )}

          <div className="pt-2 border-t border-gray-50">
            <a
              href={url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-blue-400 hover:text-blue-600 transition-colors"
            >
              원본 페이지 열기 →
            </a>
          </div>
        </div>
      )}

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

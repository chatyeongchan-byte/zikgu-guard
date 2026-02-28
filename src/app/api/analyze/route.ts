import { NextRequest, NextResponse } from "next/server";

const SCRAPER_URL = process.env.SCRAPER_URL ?? "http://localhost:4000";

// 셀러 점수 — 셀러 정보만 기반 (같은 셀러면 항상 동일)
function calcSellerScore(seller: Record<string, string>): { score: number; grade: string } {
  let score = 50;

  // 재주문율 (가장 핵심 지표)
  const reorder = parseFloat(seller.reorderRate ?? "0");
  if (reorder >= 30) score += 25;
  else if (reorder >= 20) score += 18;
  else if (reorder >= 10) score += 10;
  else if (reorder > 0) score += 5;

  // 팔로워 수
  const followers = parseInt((seller.followers ?? "0").replace(/[^0-9]/g, "")) || 0;
  if (followers >= 10000) score += 15;
  else if (followers >= 1000) score += 10;
  else if (followers >= 100) score += 5;

  // 최근 접속 여부
  const login = seller.lastLogin ?? "";
  if (login.includes("분") || login.includes("시간")) score += 10;
  else if (login.includes("天") || login.includes("일")) score += 5;

  score = Math.min(score, 100);
  const grade = score >= 85 ? "A" : score >= 70 ? "B" : score >= 55 ? "C" : score >= 40 ? "D" : "F";
  return { score, grade };
}

// 상품 점수 — 해당 상품 데이터 기반 (상품마다 다름)
function calcProductScore(data: Record<string, unknown>): { score: number; grade: string; warnings: string[] } {
  let score = 50;
  const warnings: string[] = [];

  const sales = parseInt(String(data.salesCount ?? "0").replace(/[^0-9]/g, "")) || 0;
  if (sales >= 1000) score += 25;
  else if (sales >= 100) score += 15;
  else if (sales >= 10) score += 8;
  else warnings.push("판매 이력이 적습니다.");

  const reviews = parseInt(String(data.reviewCount ?? "0").replace(/[^0-9]/g, "")) || 0;
  if (reviews >= 100) score += 15;
  else if (reviews >= 20) score += 10;
  else if (reviews >= 5) score += 5;
  else if (reviews === 0) warnings.push("리뷰가 없는 상품입니다.");

  if (data.price && data.price !== "정보 없음") score += 10;

  score = Math.min(score, 100);
  const grade = score >= 85 ? "A" : score >= 70 ? "B" : score >= 55 ? "C" : score >= 40 ? "D" : "F";
  return { score, grade, warnings };
}

export async function POST(req: NextRequest) {
  const { url, height, weight } = await req.json();

  if (!url) {
    return NextResponse.json({ error: "URL이 필요합니다." }, { status: 400 });
  }

  try {
    const scraped = await fetch(`${SCRAPER_URL}/scrape`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url, height, weight }),
    }).then((r) => r.json());

    if (scraped.error) return NextResponse.json(fallback(url));

    const seller = scraped.seller ?? {};
    const sellerScore = calcSellerScore(seller);
    const productScore = calcProductScore(scraped);
    const reviewTotal = parseInt(String(scraped.reviewCount ?? "0").replace(/[^0-9]/g, "")) || 0;

    return NextResponse.json({
      sellerName: scraped.sellerName,
      platform: scraped.platform,
      // 셀러 점수
      sellerScore: sellerScore.score,
      sellerGrade: sellerScore.grade,
      // 상품 점수
      productScore: productScore.score,
      productGrade: productScore.grade,
      warnings: productScore.warnings,
      reviews: { positive: 78, negative: 22, total: reviewTotal },
      operatingYears: "정보 수집 중",
      fakeReview: false,
      reportCount: 0,
      summary: `${scraped.platform} 셀러 "${scraped.sellerName}"`,
      raw: { productTitle: scraped.productTitle, price: scraped.price, salesCount: scraped.salesCount },
      aiSummary: scraped.aiSummary ?? null,
      mainImage: scraped.images?.mainImage ?? null,
      sizeImages: scraped.images?.sizeImages ?? [],
      sizeChart: scraped.sizeChart ?? null,
      seller: {
        id: seller.sellerId ?? "정보 없음",
        grade: seller.sellerGrade ?? "정보 없음",
        reorderRate: seller.reorderRate ?? "정보 없음",
        totalSales: seller.totalSales ?? "정보 없음",
        shopScore: seller.shopScore ?? "정보 없음",
        followers: seller.followers ?? "정보 없음",
        location: seller.location ?? "정보 없음",
        lastLogin: seller.lastLogin ?? "정보 없음",
      },
    });
  } catch {
    return NextResponse.json(fallback(url));
  }
}

function fallback(url: string) {
  return {
    sellerName: "분석 대기 중",
    platform: url.includes("weidian") ? "웨이디안" : "타오바오",
    sellerScore: 0,
    sellerGrade: "-",
    productScore: 0,
    productGrade: "-",
    warnings: ["스크래퍼 서버 미연결 — 더미 데이터 표시 중"],
    reviews: { positive: 0, negative: 0, total: 0 },
    operatingYears: "-",
    fakeReview: false,
    reportCount: 0,
    summary: "스크래퍼 서버에 연결할 수 없습니다.",
    raw: {},
    aiSummary: null,
    mainImage: null,
    sizeChart: null,
    seller: {},
  };
}

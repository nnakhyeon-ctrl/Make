export const MENU = [
  {
    group: "협력업체관리",
    items: [
      { label: "납입등록", route: "vendor/delivery" },
      { label: "거래명세서", route: "vendor/statement" },
      { label: "명세서검증조회", route: "vendor/statement-verify" },
      { label: "외상매입집계", route: "vendor/ap-summary" },
      { label: "일일구매일보", route: "vendor/daily-report" },
      { label: "자재라벨발행", route: "vendor/label" },
      { label: "자재라벨발행(PALLET)", route: "vendor/label-pallet" },
      { label: "검사성적서등록", route: "vendor/inspection-reg" },
      { label: "검사성적서조회", route: "vendor/inspection-search" },
      { label: "발주현황관리", route: "vendor/po-status" },
      { label: "협력업체입고현황", route: "vendor/inbound-status" },
    ],
  },
  {
    group: "구매관리",
    items: [
      { label: "납입등록", route: "purchase/delivery" },
      { label: "거래명세서검증", route: "purchase/statement-verify" },
      { label: "외주가공오더", route: "purchase/outsourcing-order" },
      { label: "외주가공출고", route: "purchase/outsourcing-out" },
      { label: "입고내역-PDA", route: "purchase/inbound-pda" },
      { label: "입고내역관리", route: "purchase/inbound-manage" },
      { label: "출고구매오더", route: "purchase/outbound-po" },
      { label: "공장간이동출고", route: "purchase/inter-factory" },
      { label: "담당자 호출 결과 조회", route: "purchase/call-result" },
      { label: "검사성적서조회", route: "purchase/inspection-search" },
      { label: "검사성적서", route: "purchase/inspection" },
    ],
  },
];

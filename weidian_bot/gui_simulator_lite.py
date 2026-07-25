#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Weidian H5 Simulator - Lite Version (No Browser)
- Playwright 제거, API 데이터 기반 가상 결제 화면 렌더링
- 용량 최소화 및 실행 속도 향상
"""

import customtkinter as ctk
import json
import os
import sys
from datetime import datetime
from typing import Optional, Dict, Any

# 백엔드 로직 임포트 (동일 디렉토리 가정)
try:
    from backend_api_client import WeidianAPIClient, SessionConfig
except ImportError:
    # 테스트 환경을 위한 더미 클래스 (실제 사용시 제거 가능)
    class WeidianAPIClient:
        def __init__(self, config): pass
        def get_item_info(self): return {"title": "Test Item", "price": 10000}
        def confirm_order(self): return {"ct": "dummy_ct", "token": "dummy_token", "originalPrice": 10000, "vipDiscount": 0, "finalPrice": 10000}
        def save_vip_settings(self, grade_index): return True

class VirtualPaymentFrame(ctk.CTkFrame):
    """API 데이터로 그리는 가상 결제 창 (모바일 H5 스타일)"""
    
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.configure(fg_color="#f5f5f5")  # 모바일 배경색
        
        # 상단 바
        self.header = ctk.CTkLabel(self, text="결제 페이지 (H5 시뮬레이션)", 
                                   font=ctk.CTkFont(size=16, weight="bold"),
                                   text_color="#333")
        self.header.pack(pady=10, padx=20, anchor="w")
        
        # 상품 정보 카드
        self.card = ctk.CTkFrame(self, fg_color="white", corner_radius=10)
        self.card.pack(fill="x", padx=20, pady=5)
        
        self.item_title = ctk.CTkLabel(self.card, text="상품 정보를 불러오는 중...", 
                                       font=ctk.CTkFont(size=14), text_color="#000", anchor="w")
        self.item_title.pack(padx=15, pady=(15, 5), fill="x")
        
        self.item_price = ctk.CTkLabel(self.card, text="₩ 0", 
                                       font=ctk.CTkFont(size=18, weight="bold"), 
                                       text_color="#ff5000", anchor="w")
        self.item_price.pack(padx=15, pady=(0, 15), anchor="w")
        
        # 구분선
        ctk.CTkFrame(self, height=10, fg_color="#f5f5f5").pack(fill="x")
        
        # 할인 정보 카드
        self.discount_card = ctk.CTkFrame(self, fg_color="white", corner_radius=10)
        self.discount_card.pack(fill="x", padx=20, pady=5)
        
        ctk.CTkLabel(self.discount_card, text="VIP 할인 내역", 
                     font=ctk.CTkFont(size=14, weight="bold"), text_color="#333").pack(padx=15, pady=10, anchor="w")
        
        self.vip_info_label = ctk.CTkLabel(self.discount_card, text="등급 정보 없음", 
                                           font=ctk.CTkFont(size=12), text_color="#666", anchor="w")
        self.vip_info_label.pack(padx=15, pady=(0, 5), anchor="w")
        
        self.discount_amount_label = ctk.CTkLabel(self.discount_card, text="할인액: ₩ 0", 
                                                  font=ctk.CTkFont(size=13), text_color="#00b300", anchor="w")
        self.discount_amount_label.pack(padx=15, pady=(0, 10), anchor="w")
        
        # 최종 결제 금액 (강조)
        self.total_frame = ctk.CTkFrame(self, fg_color="#fff0e6", corner_radius=10)
        self.total_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(self.total_frame, text="최종 결제 금액", 
                     font=ctk.CTkFont(size=14), text_color="#333").pack(padx=15, pady=(10, 0), anchor="w")
        
        self.final_price_label = ctk.CTkLabel(self.total_frame, text="₩ 0", 
                                              font=ctk.CTkFont(size=24, weight="bold"), 
                                              text_color="#ff5000", anchor="w")
        self.final_price_label.pack(padx=15, pady=(0, 10), anchor="w")
        
        # 상태 라벨
        self.status_label = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=12), text_color="gray")
        self.status_label.pack(pady=5)

    def update_data(self, item_data: Dict, order_data: Dict, vip_grade_name: str = ""):
        """API 데이터를 받아 UI 갱신"""
        try:
            # 상품 정보
            title = item_data.get('title', '알 수 없는 상품')
            price = item_data.get('price', 0)
            self.item_title.configure(text=title)
            self.item_price.configure(text=f"₩ {price:,}")
            
            # 할인 정보
            original = order_data.get('originalPrice', price)
            discount = order_data.get('vipDiscount', 0)
            final = order_data.get('finalPrice', original - discount)
            
            grade_text = f"적용 등급: {vip_grade_name}" if vip_grade_name else "일반 회원"
            self.vip_info_label.configure(text=grade_text)
            self.discount_amount_label.configure(text=f"할인액: - ₩ {discount:,}", 
                                                 text_color="#00b300" if discount > 0 else "#666")
            
            # 최종 금액
            self.final_price_label.configure(text=f"₩ {final:,}")
            
            # 시각적 효과 (할인 적용 시 색상 변화)
            if discount > 0:
                self.total_frame.configure(fg_color="#e6fffa")
                self.status_label.configure(text="✅ VIP 할인이 정상 적용되었습니다.", text_color="#00b300")
            else:
                self.total_frame.configure(fg_color="#fff0e6")
                self.status_label.configure(text="⚠️ 할인이 적용되지 않았습니다.", text_color="#ff5000")
                
        except Exception as e:
            self.status_label.configure(text=f"오류: {str(e)}", text_color="red")

class WeidianLiteApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("Weidian H5 Simulator (Lite)")
        self.geometry("450x750")  # 모바일 세로 비율
        self.resizable(False, False)
        
        # 설정 변수
        self.shop_id = "123456"  # 실제 값으로 변경 필요
        self.cookies_path = "cookies.json"
        self.client: Optional[WeidianAPIClient] = None
        self.current_vip_grade = "일반"
        
        # 레이아웃 구성
        self._setup_ui()
        
    def _setup_ui(self):
        # 상단 컨트롤 패널
        control_frame = ctk.CTkFrame(self, fg_color="#333333")
        control_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(control_frame, text="세션 관리", text_color="white").pack(pady=5)
        
        self.btn_load_cookie = ctk.CTkButton(control_frame, text="📂 쿠키 로드", command=self.load_cookies, width=140)
        self.btn_load_cookie.pack(pady=5)
        
        self.lbl_session_status = ctk.CTkLabel(control_frame, text="상태: 연결 안됨", text_color="gray", font=ctk.CTkFont(size=11))
        self.lbl_session_status.pack(pady=5)
        
        # 메인 시뮬레이션 영역 (스크롤 가능)
        self.scroll_view = ctk.CTkScrollableFrame(self, label_text="실시간 결제 시뮬레이션")
        self.scroll_view.pack(fill="both", expand=True, padx=10, pady=10)
        
        # 가상 결제 창 위젯
        self.payment_view = VirtualPaymentFrame(self.scroll_view)
        self.payment_view.pack(fill="x", pady=10)
        
        # 하단 조작 패널
        action_frame = ctk.CTkFrame(self)
        action_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(action_frame, text="VIP 등급 조작", font=ctk.CTkFont(weight="bold")).pack(pady=5)
        
        self.grade_var = ctk.StringVar(value="일반 (0)")
        self.combo_grade = ctk.CTkComboBox(action_frame, variable=self.grade_var, 
                                           values=["일반 (0)", "VIP 1 단계 (1)", "VIP 2 단계 (2)", "VIP 3 단계 (3)"],
                                           width=200)
        self.combo_grade.pack(pady=5)
        
        self.btn_apply = ctk.CTkButton(action_frame, text="⭐ 등급 변경 및 재계산", 
                                       command=self.apply_vip_and_refresh, 
                                       fg_color="#ff5000", hover_color="#cc4000")
        self.btn_apply.pack(pady=10)
        
        # 로그 콘솔 (작게)
        self.log_text = ctk.CTkTextbox(self, height=100, font=ctk.CTkFont(size=10))
        self.log_text.pack(fill="x", padx=10, pady=(0, 10))
        self.log_text.insert("0.0", "시스템 준비 완료. 쿠키를 로드하세요.\n")
        self.log_text.configure(state="disabled")
        
    def log(self, message: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"[{timestamp}] {message}\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")
        
    def load_cookies(self):
        if not os.path.exists(self.cookies_path):
            self.log("❌ cookies.json 파일을 찾을 수 없습니다.")
            # 더미 모드로 시작 (테스트용)
            self.log("⚠️ 데모 모드로 시작합니다. (실제 API 호출 불가)")
            self.client = WeidianAPIClient(SessionConfig(cookies={}))
            self.lbl_session_status.configure(text="상태: 데모 모드", text_color="orange")
            self.btn_apply.configure(state="normal")
            return

        try:
            with open(self.cookies_path, 'r', encoding='utf-8') as f:
                cookies = json.load(f)
            
            config = SessionConfig(cookies=cookies, shop_id=self.shop_id)
            self.client = WeidianAPIClient(config)
            self.lbl_session_status.configure(text="상태: 연결됨 (실제)", text_color="#00b300")
            self.log("✅ 쿠키 로드 성공. 세션 초기화 완료.")
            
            # 초기 데이터 조회
            self.refresh_display()
            
        except Exception as e:
            self.log(f"❌ 쿠키 로드 실패: {str(e)}")
            self.client = None

    def refresh_display(self):
        if not self.client:
            return
            
        try:
            self.log("🔄 상품 정보 조회 중...")
            item_info = self.client.get_item_info()
            
            self.log("🔄 주문 사전 검증 (Confirm) 중...")
            # 실제 API 호출 시 여기서 grade 파라미터 등을 조절할 수 있음
            order_info = self.client.confirm_order() 
            
            self.payment_view.update_data(item_info, order_info, self.current_vip_grade)
            self.log("✅ 화면 갱신 완료.")
            
        except Exception as e:
            self.log(f"❌ 데이터 갱신 오류: {str(e)}")
            # 에러 시 더미 데이터로 화면이라도 보여줌 (UX)
            dummy_order = {"originalPrice": 50000, "vipDiscount": 0, "finalPrice": 50000}
            dummy_item = {"title": "연결 오류 (데모)", "price": 50000}
            self.payment_view.update_data(dummy_item, dummy_order, "연결안됨")

    def apply_vip_and_refresh(self):
        if not self.client:
            self.log("⚠️ 먼저 쿠키를 로드해주세요.")
            return
            
        grade_str = self.grade_var.get()
        grade_index = int(grade_str.split("(")[1].replace(")", ""))
        grade_name = grade_str.split("(")[0].strip()
        
        self.log(f"🚀 VIP 등급 변경 요청: {grade_name} (Index: {grade_index})")
        
        try:
            # 1. VIP 설정 저장 API 호출
            success = self.client.save_vip_settings(grade_index)
            if success:
                self.log("✅ 등급 설정 저장 성공.")
                self.current_vip_grade = grade_name
                # 2. 화면 갱신 (할인 적용 여부 확인)
                self.refresh_display()
            else:
                self.log("❌ 등급 설정 저장 실패.")
        except Exception as e:
            self.log(f"❌ API 호출 중 오류: {str(e)}")
            # 데모 모드인 경우 강제로 UI만 업데이트하여 동작 보여줌
            if "데모" in self.lbl_session_status.cget("text"):
                self.log("⚠️ 데모 모드: UI 만 업데이트합니다.")
                self.current_vip_grade = grade_name
                # 할인 시뮬레이션 (데모)
                demo_order = {"originalPrice": 50000, "vipDiscount": 5000 * (grade_index + 1), "finalPrice": 50000 - (5000 * (grade_index + 1))}
                demo_item = {"title": "데모 상품 (가상)", "price": 50000}
                self.payment_view.update_data(demo_item, demo_order, grade_name)

if __name__ == "__main__":
    # 다크 모드 설정
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    
    app = WeidianLiteApp()
    app.mainloop()

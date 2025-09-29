# -*- coding: utf-8 -*-
"""
Smart Assistant 메인 GUI 윈도우
"""
import sys
import os
import asyncio
import json
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

from PyQt6.QtGui import QFont, QFontDatabase
from PyQt6.QtWidgets import QApplication, QStyleFactory


# Windows 한글 출력 설정
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    os.environ['PYTHONUTF8'] = '1'

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTextEdit, QTabWidget, QTableWidget, QTableWidgetItem,
    QHeaderView, QGroupBox, QGridLayout, QLineEdit, QComboBox, QCheckBox,
    QProgressBar, QStatusBar, QMenuBar, QMenu, QMessageBox, QSplitter,
    QFrame, QScrollArea, QListWidget, QListWidgetItem
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize
from PyQt6.QtGui import QFont, QIcon, QPixmap, QPalette, QColor

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from main import SmartAssistant


class WorkerThread(QThread):
    """백그라운드 작업 스레드"""
    progress_updated = pyqtSignal(int)
    status_updated = pyqtSignal(str)
    result_ready = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, assistant, email_config, messenger_config):
        super().__init__()
        self.assistant = assistant
        self.email_config = email_config
        self.messenger_config = messenger_config
        self._should_stop = False
    
    def run(self):
        try:
            # 비동기 작업을 동기적으로 실행
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            self.status_updated.emit("시스템 초기화 중...")
            loop.run_until_complete(self.assistant.initialize(self.email_config, self.messenger_config))
            
            self.status_updated.emit("메시지 수집 중...")
            self.progress_updated.emit(20)
            
            messages = loop.run_until_complete(self.assistant.collect_messages(10, 10))
            
            if not messages:
                self.error_occurred.emit("수집된 메시지가 없습니다.")
                return
            
            self.status_updated.emit("AI 분석 중...")
            self.progress_updated.emit(50)
            
            analysis_results = loop.run_until_complete(self.assistant.analyze_messages())
            
            self.status_updated.emit("TODO 리스트 생성 중...")
            self.progress_updated.emit(80)
            
            todo_list = loop.run_until_complete(self.assistant.generate_todo_list(analysis_results))
            
            self.progress_updated.emit(100)
            self.status_updated.emit("완료")
            
            result = {
                "success": True,
                "todo_list": todo_list,
                "analysis_results": analysis_results,
                "messages": messages
            }
            
            self.result_ready.emit(result)
            
        except Exception as e:
            self.error_occurred.emit(f"오류 발생: {str(e)}")
        finally:
            loop.close()
    
    def stop(self):
        self._should_stop = True


class StatusIndicator(QLabel):
    """상태 표시기"""
    def __init__(self, text="오프라인"):
        super().__init__(text)
        self.setFixedSize(100, 30)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("""
            QLabel {
                border: 2px solid #ccc;
                border-radius: 15px;
                background-color: #f0f0f0;
                color: #666;
                font-weight: bold;
            }
        """)
        self.current_status = "offline"
    
    def set_status(self, status):
        self.current_status = status
        if status == "online":
            self.setText("온라인")
            self.setStyleSheet("""
                QLabel {
                    border: 2px solid #4CAF50;
                    border-radius: 15px;
                    background-color: #E8F5E8;
                    color: #2E7D32;
                    font-weight: bold;
                }
            """)
        else:
            self.setText("오프라인")
            self.setStyleSheet("""
                QLabel {
                    border: 2px solid #ccc;
                    border-radius: 15px;
                    background-color: #f0f0f0;
                    color: #666;
                    font-weight: bold;
                }
            """)

class TodoItemWidget(QWidget):
    """TODO 아이템 위젯(통일 스타일)"""
    PRIORITY_COLORS = {
        "high":   ("High",   "#FEE2E2", "#991B1B"),   # red
        "medium": ("Medium", "#FEF3C7", "#92400E"),   # amber
        "low":    ("Low",    "#DCFCE7", "#166534"),   # green
    }

    def __init__(self, todo_item):
        super().__init__()
        self.todo_item = todo_item
        self.setMinimumHeight(64)
        self.init_ui()

    def init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 8, 12, 8)
        root.setSpacing(6)

        # 1) 상단: 제목 + 우선순위칩 + 상태칩
        top = QHBoxLayout()
        top.setSpacing(8)

        title = QLabel(self.todo_item.get("title", ""))
        title.setStyleSheet("font-weight: 700;")
        top.addWidget(title, 1)

        # priority chip
        pr = self.todo_item.get("priority", "low")
        text, bg, fg = self.PRIORITY_COLORS.get(pr, self.PRIORITY_COLORS["low"])
        top.addWidget(Chip(text, bg, fg), 0)

        # status chip
        status_txt = self.todo_item.get("status", "pending").capitalize()
        top.addWidget(Chip(status_txt, "#E0E7FF", "#3730A3"), 0)

        root.addLayout(top)

        # 2) 하단: 메타 정보(요청자/타입/데드라인)
        meta = QHBoxLayout()
        meta.setSpacing(12)

        requester = Chip(f"요청자 · {self.todo_item.get('requester','')}", "#F3F4F6", "#374151")
        typechip  = Chip(f"유형 · {self.todo_item.get('type','')}", "#F3F4F6", "#374151")
        meta.addWidget(requester, 0)
        meta.addWidget(typechip, 0)

        deadline = self.todo_item.get("deadline")
        if deadline:
            meta.addWidget(Chip(f"마감 · {deadline}", "#FFE4E6", "#9F1239"), 0)

        meta.addStretch(1)
        root.addLayout(meta)

        # 카드 스타일
        self.setStyleSheet("""
            QWidget {
                border: 1px solid #E5E7EB;
                border-radius: 10px;
                background: #FFFFFF;
            }
            QWidget:hover { border-color: #60A5FA; background: #F8FAFC; }
        """)

# class TodoItemWidget(QWidget):
#     """TODO 아이템 위젯"""
#     def __init__(self, todo_item):
#         super().__init__()
#         self.todo_item = todo_item
#         self.init_ui()
    
#     def init_ui(self):
#         layout = QVBoxLayout(self)
#         layout.setContentsMargins(10, 5, 10, 5)
        
#         # 제목과 우선순위
#         title_layout = QHBoxLayout()
        
#         priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}
#         icon = priority_icon.get(self.todo_item.get("priority", "low"), "⚪")
        
#         self.title_label = QLabel(f"{icon} {self.todo_item.get('title', '')}")
#         self.title_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
#         title_layout.addWidget(self.title_label)
        
#         title_layout.addStretch()
        
#         # 상태 표시
#         self.status_label = QLabel(self.todo_item.get("status", "pending"))
#         self.status_label.setStyleSheet("color: #666; font-size: 9px;")
#         title_layout.addWidget(self.status_label)
        
#         layout.addLayout(title_layout)
        
#         # 요청자와 타입
#         info_layout = QHBoxLayout()
#         self.requester_label = QLabel(f"👤 {self.todo_item.get('requester', '')}")
#         self.requester_label.setStyleSheet("color: #666; font-size: 9px;")
#         info_layout.addWidget(self.requester_label)
        
#         info_layout.addStretch()
        
#         self.type_label = QLabel(f"🏷️ {self.todo_item.get('type', '')}")
#         self.type_label.setStyleSheet("color: #666; font-size: 9px;")
#         info_layout.addWidget(self.type_label)
        
#         layout.addLayout(info_layout)
        
#         # 데드라인
#         if self.todo_item.get('deadline'):
#             self.deadline_label = QLabel(f"⏰ {self.todo_item.get('deadline')}")
#             self.deadline_label.setStyleSheet("color: #e74c3c; font-size: 9px; font-weight: bold;")
#             layout.addWidget(self.deadline_label)
        
#         # 스타일링
#         self.setStyleSheet("""
#             QWidget {
#                 border: 1px solid #ddd;
#                 border-radius: 5px;
#                 background-color: white;
#                 margin: 2px;
#             }
#             QWidget:hover {
#                 border-color: #4CAF50;
#                 background-color: #f8f9fa;
#             }
#         """)

class EmojiLabel(QLabel):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        f = self.font()
        f.setFamily("Segoe UI Emoji")  # 이모지 전용 폰트
        self.setFont(f)


class SmartAssistantGUI(QMainWindow):
    """Smart Assistant 메인 GUI"""
    
    def __init__(self):
        super().__init__()
        self.assistant = SmartAssistant()
        self.worker_thread = None
        self.current_status = "offline"
        self.email_config = {}
        self.messenger_config = {"use_simulator": True}
        
        self.init_ui()
        self.setup_timers()
    
    def init_ui(self):
        """UI 초기화"""
        self.setWindowTitle("Smart Assistant v1.0")
        self.setGeometry(100, 100, 1400, 900)
        
        # 중앙 위젯 설정
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 메인 레이아웃
        main_layout = QHBoxLayout(central_widget)
        
        # 좌측 패널 (설정 및 제어)
        left_panel = self.create_left_panel()
        main_layout.addWidget(left_panel, 1)
        
        # 우측 패널 (결과 표시)
        right_panel = self.create_right_panel()
        main_layout.addWidget(right_panel, 2)
        
        # 메뉴바 설정
        self.create_menu_bar()
        
        # 상태바 설정
        self.create_status_bar()
    
    def create_left_panel(self):
        """좌측 패널 생성"""
        panel = QFrame()
        panel.setFrameStyle(QFrame.Shape.StyledPanel)
        panel.setMaximumWidth(350)
        
        layout = QVBoxLayout(panel)
        
        # 제목
        title = QLabel("Smart Assistant")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #2c3e50; margin: 10px;")
        layout.addWidget(title)
        
        # 상태 표시기
        status_group = QGroupBox("연결 상태")
        status_layout = QVBoxLayout(status_group)
        
        self.status_indicator = StatusIndicator()
        status_layout.addWidget(self.status_indicator)
        
        # 상태 토글 버튼
        self.status_button = QPushButton("오프라인 → 온라인")
        self.status_button.clicked.connect(self.toggle_status)
        self.status_button.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 8px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        status_layout.addWidget(self.status_button)
        
        layout.addWidget(status_group)
        
        # 이메일 설정
        email_group = QGroupBox("이메일 설정")
        email_layout = QVBoxLayout(email_group)
        
        # 이메일 주소
        email_layout.addWidget(QLabel("이메일 주소:"))
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("example@naver.com")
        email_layout.addWidget(self.email_input)
        
        # 비밀번호
        email_layout.addWidget(QLabel("비밀번호/앱 비밀번호:"))
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("이메일 비밀번호")
        email_layout.addWidget(self.password_input)
        
        # 제공자 선택
        email_layout.addWidget(QLabel("이메일 제공자:"))
        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["naver", "gmail", "daum"])
        email_layout.addWidget(self.provider_combo)
        
        layout.addWidget(email_group)
        
        # 제어 버튼
        control_group = QGroupBox("제어")
        control_layout = QVBoxLayout(control_group)
        
        # 시작 버튼
        self.start_button = QPushButton("🔄 메시지 수집 시작")
        self.start_button.clicked.connect(self.start_collection)
        self.start_button.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                padding: 12px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #229954;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
        """)
        control_layout.addWidget(self.start_button)
        
        # 중지 버튼
        self.stop_button = QPushButton("⏹️ 수집 중지")
        self.stop_button.clicked.connect(self.stop_collection)
        self.stop_button.setEnabled(False)
        self.stop_button.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                padding: 12px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
        """)
        control_layout.addWidget(self.stop_button)
        
        # 오프라인 정리 버튼
        self.cleanup_button = QPushButton("🧹 오프라인 정리")
        self.cleanup_button.clicked.connect(self.offline_cleanup)
        self.cleanup_button.setStyleSheet("""
            QPushButton {
                background-color: #f39c12;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e67e22;
            }
        """)
        control_layout.addWidget(self.cleanup_button)
        
        layout.addWidget(control_group)
        
        # 진행률 표시
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # 상태 메시지
        self.status_message = QLabel("준비됨")
        self.status_message.setStyleSheet("color: #666; font-size: 12px; padding: 5px;")
        layout.addWidget(self.status_message)
        
        layout.addStretch()
        
        return panel
    
    def create_right_panel(self):
        """우측 패널 생성"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # 탭 위젯
        self.tab_widget = QTabWidget()
        
        # TODO 리스트 탭
        self.todo_tab = self.create_todo_tab()
        self.tab_widget.addTab(self.todo_tab, "📋 TODO 리스트")
        
        # 메시지 탭
        self.message_tab = self.create_message_tab()
        self.tab_widget.addTab(self.message_tab, "📨 메시지")
        
        # 분석 결과 탭
        self.analysis_tab = self.create_analysis_tab()
        self.tab_widget.addTab(self.analysis_tab, "📊 분석 결과")
        
        layout.addWidget(self.tab_widget)
        
        return panel
    
    # def create_todo_tab(self):
 
    #     tab = QWidget()
    #     layout = QVBoxLayout(tab)

    #     self.todo_list = QListWidget()
    #     self.todo_list.setStyleSheet("""
    #         QListWidget {
    #             border: 1px solid #ddd;
    #             border-radius: 5px;
    #             background-color: #f8f9fa;
    #         }
    #         QListWidget::item {
    #             padding: 5px;
    #             border-bottom: 1px solid #eee;
    #         }
    #         QListWidget::item:selected {
    #             background-color: #e3f2fd;
    #         }
    #     """)
    #     layout.addWidget(self.todo_list)
        
    #     return tab
    def create_todo_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        self.todo_list = QListWidget()
        self.todo_list.setUniformItemSizes(True)      # 행 높이 균일
        self.todo_list.setSpacing(6)
        self.todo_list.setStyleSheet("""
            QListWidget::item { padding: 0px; margin: 4px; }
            QListWidget { background: #F8FAFC; }
        """)
        layout.addWidget(self.todo_list)
        return tab

    def update_message_table(self, messages):
        self.message_table.setRowCount(len(messages))
        self.message_table.verticalHeader().setDefaultSectionSize(36)  # 고정 행 높이
        self.message_table.setWordWrap(False)

        for i, msg in enumerate(messages):
            def item(text):  # 엘라이드용
                it = QTableWidgetItem(text or "")
                it.setToolTip(text or "")
                return it

            self.message_table.setItem(i, 0, item(msg.get("platform", "")))
            self.message_table.setItem(i, 1, item(msg.get("sender", "")))

            content = msg.get("subject") or (msg.get("content", "")[:120])
            self.message_table.setItem(i, 2, item(content))

            date_str = msg.get("date", "")
            if date_str:
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    date_str = dt.strftime("%m-%d %H:%M")
                except:
                    pass
            self.message_table.setItem(i, 3, item(date_str))

    
    def create_message_tab(self):
        """메시지 탭 생성"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 메시지 테이블
        self.message_table = QTableWidget()
        self.message_table.setColumnCount(4)
        self.message_table.setHorizontalHeaderLabels(["플랫폼", "발신자", "제목/내용", "날짜"])
        self.message_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        layout.addWidget(self.message_table)
        
        return tab
    
    def create_analysis_tab(self):
        """분석 결과 탭 생성"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 분석 결과 텍스트
        self.analysis_text = QTextEdit()
        self.analysis_text.setReadOnly(True)
        self.analysis_text.setPlaceholderText("분석 결과가 여기에 표시됩니다.")
        
        layout.addWidget(self.analysis_text)
        
        return tab
    
    def create_menu_bar(self):
        """메뉴바 생성"""
        menubar = self.menuBar()
        
        # 파일 메뉴
        file_menu = menubar.addMenu("파일")
        
        save_action = file_menu.addAction("결과 저장")
        save_action.triggered.connect(self.save_results)
        
        load_action = file_menu.addAction("결과 불러오기")
        load_action.triggered.connect(self.load_results)
        
        file_menu.addSeparator()
        
        exit_action = file_menu.addAction("종료")
        exit_action.triggered.connect(self.close)
        
        # 도움말 메뉴
        help_menu = menubar.addMenu("도움말")
        
        about_action = help_menu.addAction("정보")
        about_action.triggered.connect(self.show_about)
    
    def create_status_bar(self):
        """상태바 생성"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Smart Assistant 준비됨")
    
    def setup_timers(self):
        """타이머 설정"""
        # 자동 새로고침 타이머 (온라인 모드에서만)
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.auto_refresh)
        self.refresh_timer.setInterval(300000)  # 5분마다
    
    def toggle_status(self):
        """상태 토글"""
        if self.current_status == "offline":
            self.current_status = "online"
            self.status_indicator.set_status("online")
            self.status_button.setText("온라인 → 오프라인")
            self.status_button.setStyleSheet("""
                QPushButton {
                    background-color: #e74c3c;
                    color: white;
                    border: none;
                    padding: 8px;
                    border-radius: 4px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #c0392b;
                }
            """)
            self.refresh_timer.start()
            self.status_bar.showMessage("온라인 모드 - 자동 모니터링 활성화")
        else:
            self.current_status = "offline"
            self.status_indicator.set_status("offline")
            self.status_button.setText("오프라인 → 온라인")
            self.status_button.setStyleSheet("""
                QPushButton {
                    background-color: #3498db;
                    color: white;
                    border: none;
                    padding: 8px;
                    border-radius: 4px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #2980b9;
                }
            """)
            self.refresh_timer.stop()
            self.status_bar.showMessage("오프라인 모드")
    
    def start_collection(self):
        """메시지 수집 시작"""
        # 이메일 설정 확인
        email = self.email_input.text().strip()
        password = self.password_input.text().strip()
        
        if not email:
            QMessageBox.warning(self, "입력 오류", "이메일 주소를 입력해주세요.")
            return
        
        self.email_config = {
            "email": email,
            "password": password,
            "provider": self.provider_combo.currentText()
        }
        
        # UI 상태 변경
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # 워커 스레드 시작
        self.worker_thread = WorkerThread(self.assistant, self.email_config, self.messenger_config)
        self.worker_thread.progress_updated.connect(self.progress_bar.setValue)
        self.worker_thread.status_updated.connect(self.status_message.setText)
        self.worker_thread.result_ready.connect(self.handle_result)
        self.worker_thread.error_occurred.connect(self.handle_error)
        self.worker_thread.start()
    
    def stop_collection(self):
        """수집 중지"""
        if self.worker_thread and self.worker_thread.isRunning():
            self.worker_thread.stop()
            self.worker_thread.wait(3000)
        
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.status_message.setText("수집 중지됨")
    
    def handle_result(self, result):
        """결과 처리"""
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.status_message.setText("수집 완료")
        
        if result.get("success"):
            todo_list = result["todo_list"]
            
            # TODO 리스트 업데이트
            self.update_todo_list(todo_list["items"])
            
            # 메시지 테이블 업데이트
            self.update_message_table(result["messages"])
            
            # 분석 결과 업데이트
            self.update_analysis_results(result["analysis_results"])
            
            self.status_bar.showMessage(f"수집 완료: {todo_list['total_items']}개 TODO 생성")
            
            # 자동 저장
            self.auto_save_results(result)
        else:
            QMessageBox.critical(self, "오류", "수집 중 오류가 발생했습니다.")
    
    def handle_error(self, error_message):
        """오류 처리"""
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.status_message.setText("오류 발생")
        
        QMessageBox.critical(self, "오류", error_message)
    
    def update_todo_list(self, todo_items):
        """TODO 리스트 업데이트"""
        self.todo_list.clear()
        
        for item in todo_items[:20]:  # 상위 20개만 표시
            todo_widget = TodoItemWidget(item)
            list_item = QListWidgetItem()
            list_item.setSizeHint(todo_widget.sizeHint())
            
            self.todo_list.addItem(list_item)
            self.todo_list.setItemWidget(list_item, todo_widget)
    
    def update_message_table(self, messages):
        """메시지 테이블 업데이트"""
        self.message_table.setRowCount(len(messages))
        
        for i, msg in enumerate(messages):
            self.message_table.setItem(i, 0, QTableWidgetItem(msg.get("platform", "")))
            self.message_table.setItem(i, 1, QTableWidgetItem(msg.get("sender", "")))
            
            content = msg.get("subject", "") or msg.get("content", "")[:100]
            self.message_table.setItem(i, 2, QTableWidgetItem(content))
            
            date_str = msg.get("date", "")
            if date_str:
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    date_str = dt.strftime("%m-%d %H:%M")
                except:
                    pass
            
            self.message_table.setItem(i, 3, QTableWidgetItem(date_str))
    
    def update_analysis_results(self, analysis_results):
        """분석 결과 업데이트"""
        result_text = "📊 분석 결과 요약\n"
        result_text += "=" * 50 + "\n\n"
        
        for i, result in enumerate(analysis_results[:10], 1):
            msg = result["message"]
            priority = result["priority"]
            summary = result.get("summary")
            
            result_text += f"{i}. [{priority['priority_level'].upper()}] {msg['sender']}\n"
            result_text += f"   플랫폼: {msg['platform']}\n"
            result_text += f"   우선순위 점수: {priority['overall_score']:.2f}\n"
            
            if summary:
                result_text += f"   요약: {summary['summary']}\n"
            
            result_text += f"   액션: {len(result['actions'])}개\n\n"
        
        self.analysis_text.setText(result_text)
    
    def auto_refresh(self):
        """자동 새로고침 (온라인 모드)"""
        if self.current_status == "online" and not self.worker_thread:
            self.start_collection()
    
    def offline_cleanup(self):
        """오프라인 정리"""
        from ui.offline_cleaner import OfflineCleanupDialog
        
        dialog = OfflineCleanupDialog(self)
        dialog.exec()
    
    def auto_save_results(self, result):
        """결과 자동 저장"""
        try:
            filename = f"gui_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"자동 저장 오류: {e}")
    
    def save_results(self):
        """결과 저장"""
        QMessageBox.information(self, "저장", "결과 저장 기능은 향후 구현될 예정입니다.")
    
    def load_results(self):
        """결과 불러오기"""
        QMessageBox.information(self, "불러오기", "결과 불러오기 기능은 향후 구현될 예정입니다.")
    
    def show_about(self):
        """정보 표시"""
        QMessageBox.about(self, "Smart Assistant 정보",
                         "Smart Assistant v1.0\n\n"
                         "AI 기반 스마트 어시스턴트\n"
                         "이메일과 메신저 메시지를 분석하여\n"
                         "TODO 리스트를 자동 생성합니다.\n\n"
                         "개발: Smart Assistant Team")
    
    def closeEvent(self, event):
        """창 닫기 이벤트"""
        if self.worker_thread and self.worker_thread.isRunning():
            self.worker_thread.stop()
            self.worker_thread.wait(3000)
        
        event.accept()

class Chip(QLabel):
    def __init__(self, text, bg="#E5E7EB", fg="#111827"):
        super().__init__(text)
        self.setProperty("chip", True)
        self.setStyleSheet(f"""
            QLabel[chip="true"] {{
                background: {bg};
                color: {fg};
                padding: 2px 8px;
                border-radius: 999px;
                font-weight: 600;
            }}
        """)

# def main():
#     """메인 함수"""
#     app = QApplication(sys.argv)
#     app.setApplicationName("Smart Assistant")
#     app.setApplicationVersion("1.0")
    
#     window = SmartAssistantGUI()
#     window.show()
    
#     sys.exit(app.exec())

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Smart Assistant")
    app.setApplicationVersion("1.0")

    # 1) OS 일관 테마
    app.setStyle(QStyleFactory.create("Fusion"))

    # 2) 전역 기본 글꼴(한글)
    #  - 윈도우: 맑은 고딕이 가장 안정적
    #  - Noto Sans KR 폰트를 동봉했다면 addApplicationFont로 등록 후 이름만 바꾸면 됩니다.
    base_korean_font = QFont("Malgun Gothic", 10)
    app.setFont(base_korean_font)

    # 3) 전역 팔레트(살짝 명도 올린 중립 톤)
    from PyQt6.QtGui import QPalette, QColor
    pal = app.palette()
    pal.setColor(QPalette.ColorRole.Window, QColor("#FAFAFA"))
    pal.setColor(QPalette.ColorRole.Base,   QColor("#FFFFFF"))
    pal.setColor(QPalette.ColorRole.Text,   QColor("#222222"))
    pal.setColor(QPalette.ColorRole.Button, QColor("#FFFFFF"))
    app.setPalette(pal)

    # 4) 전역 스타일시트(여백/모서리/폰트크기 통일)
    app.setStyleSheet("""
        * { font-size: 12px; }
        QGroupBox { font-weight: 600; border: 1px solid #E5E7EB; border-radius: 8px; margin-top: 8px; }
        QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; color:#111827; }
        QLabel[role="title"] { font-size: 18px; font-weight: 800; color:#1F2937; }
        QPushButton {
            border: 0; border-radius: 8px; padding: 10px 12px; font-weight: 700;
        }
        QTableWidget, QListWidget {
            border: 1px solid #E5E7EB; border-radius: 8px; background: #FFFFFF;
        }
        QHeaderView::section {
            background: #F3F4F6; border: 0; padding: 8px; font-weight: 600;
        }
    """)

    window = SmartAssistantGUI()
    window.show()
    sys.exit(app.exec())



if __name__ == "__main__":
    main()

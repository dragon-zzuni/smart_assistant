# ui/todo_panel.py
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel

from PyQt6.QtCore import QTimer

class TodoPanel(QWidget):
    def __init__(self, db_path="todos.db", parent=None):
        super().__init__(parent)
        self.conn = get_conn(db_path)
        init_db(self.conn)
        self.setup_ui()

        # 1분마다 스누즈 체크
        self.snooze_timer = QTimer(self)
        self.snooze_timer.setInterval(60 * 1000)  # 60초
        self.snooze_timer.timeout.connect(self.on_snooze_timer)
        self.snooze_timer.start()

        # 앱 시작시 즉시 체크
        self.on_snooze_timer()

    def on_snooze_timer(self):
        check_snoozes_and_deadlines(self.conn)
        self.refresh_todo_list()  # DB에서 다시 로드하여 UI 갱신

    def refresh_todo_list(self):
        # DB에서 status!='done' 등 원하는 필터로 로드
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM todos WHERE status!='done' ORDER BY created_at DESC")
        rows = cur.fetchall()
        self.todo_list.clear()
        for r in rows:
            widget = TodoItemWidget(dict(r))
            item = QListWidgetItem()
            item.setSizeHint(widget.sizeHint())
            self.todo_list.addItem(item)
            self.todo_list.setItemWidget(item, widget)
            # TodoItemWidget 내부에서 완료/스누즈 버튼 누르면 위의 DB 함수 호출 & refresh_todo_list 실행

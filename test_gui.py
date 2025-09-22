# -*- coding: utf-8 -*-
"""
GUI 테스트 스크립트
"""
import sys
import os
from pathlib import Path

# Windows 한글 출력 설정
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    os.environ['PYTHONUTF8'] = '1'

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_imports():
    """필수 모듈 import 테스트"""
    print("🧪 GUI 모듈 import 테스트...")
    
    try:
        from PyQt6.QtWidgets import QApplication
        print("✅ PyQt6.QtWidgets import 성공")
    except ImportError as e:
        print(f"❌ PyQt6.QtWidgets import 실패: {e}")
        return False
    
    try:
        from ui.main_window import SmartAssistantGUI
        print("✅ SmartAssistantGUI import 성공")
    except ImportError as e:
        print(f"❌ SmartAssistantGUI import 실패: {e}")
        return False
    
    try:
        from ui.offline_cleaner import OfflineCleanupDialog
        print("✅ OfflineCleanupDialog import 성공")
    except ImportError as e:
        print(f"❌ OfflineCleanupDialog import 실패: {e}")
        return False
    
    try:
        from main import SmartAssistant
        print("✅ SmartAssistant import 성공")
    except ImportError as e:
        print(f"❌ SmartAssistant import 실패: {e}")
        return False
    
    print("✅ 모든 모듈 import 성공!")
    return True

def test_gui_creation():
    """GUI 생성 테스트"""
    print("\n🖥️ GUI 생성 테스트...")
    
    try:
        from PyQt6.QtWidgets import QApplication
        from ui.main_window import SmartAssistantGUI
        
        app = QApplication(sys.argv)
        window = SmartAssistantGUI()
        
        print("✅ GUI 윈도우 생성 성공")
        print(f"   윈도우 크기: {window.size().width()}x{window.size().height()}")
        print(f"   윈도우 제목: {window.windowTitle()}")
        
        # GUI 요소 확인
        if hasattr(window, 'status_indicator'):
            print("✅ 상태 표시기 생성 성공")
        
        if hasattr(window, 'start_button'):
            print("✅ 시작 버튼 생성 성공")
        
        if hasattr(window, 'tab_widget'):
            print("✅ 탭 위젯 생성 성공")
        
        window.close()
        app.quit()
        
        print("✅ GUI 생성 테스트 완료!")
        return True
        
    except Exception as e:
        print(f"❌ GUI 생성 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_offline_cleaner():
    """오프라인 정리 기능 테스트"""
    print("\n🧹 오프라인 정리 기능 테스트...")
    
    try:
        from PyQt6.QtWidgets import QApplication
        from ui.offline_cleaner import OfflineCleanupDialog
        
        app = QApplication(sys.argv)
        dialog = OfflineCleanupDialog()
        
        print("✅ 오프라인 정리 대화상자 생성 성공")
        print(f"   대화상자 크기: {dialog.size().width()}x{dialog.size().height()}")
        print(f"   대화상자 제목: {dialog.windowTitle()}")
        
        # UI 요소 확인
        if hasattr(dialog, 'results_table'):
            print("✅ 결과 테이블 생성 성공")
        
        if hasattr(dialog, 'start_button'):
            print("✅ 시작 버튼 생성 성공")
        
        dialog.close()
        app.quit()
        
        print("✅ 오프라인 정리 기능 테스트 완료!")
        return True
        
    except Exception as e:
        print(f"❌ 오프라인 정리 기능 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """메인 테스트 함수"""
    print("🚀 Smart Assistant GUI 테스트 시작")
    print("=" * 50)
    
    tests = [
        ("모듈 Import", test_imports),
        ("GUI 생성", test_gui_creation),
        ("오프라인 정리", test_offline_cleaner)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name} 테스트...")
        if test_func():
            passed += 1
        else:
            print(f"❌ {test_name} 테스트 실패")
    
    print(f"\n📊 테스트 결과: {passed}/{total} 통과")
    
    if passed == total:
        print("🎉 모든 테스트 통과! GUI가 정상적으로 작동합니다.")
        print("\n실행 방법:")
        print("  py run_gui.py")
        print("  또는 run_gui.bat 더블클릭")
    else:
        print("❌ 일부 테스트 실패. 문제를 해결한 후 다시 시도해주세요.")

if __name__ == "__main__":
    main()

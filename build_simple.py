# -*- coding: utf-8 -*-
"""
간단한 exe 빌드 스크립트
"""
import os
import subprocess
import sys

def build_exe():
    """exe 파일 빌드"""
    print("🔨 Smart Assistant exe 빌드 시작...")
    
    # PyInstaller 설치 확인
    try:
        import PyInstaller
        print("✅ PyInstaller가 설치되어 있습니다.")
    except ImportError:
        print("❌ PyInstaller가 설치되지 않았습니다. 설치 중...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        print("✅ PyInstaller 설치 완료")
    
    # 간단한 빌드 명령어
    build_command = [
        "pyinstaller",
        "--onefile",
        "--windowed",
        "--name=SmartAssistant",
        "run_gui.py"
    ]
    
    print("🔨 빌드 명령어:", " ".join(build_command))
    
    try:
        # 빌드 실행
        subprocess.check_call(build_command)
        print("✅ exe 파일 빌드 완료!")
        print("📁 dist/SmartAssistant.exe 파일을 확인하세요.")
        
        # 빌드 결과 확인
        exe_path = "dist/SmartAssistant.exe"
        if os.path.exists(exe_path):
            size_mb = os.path.getsize(exe_path) / (1024 * 1024)
            print(f"📊 파일 크기: {size_mb:.1f} MB")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ 빌드 실패: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("Smart Assistant exe 빌드 도구")
    print("=" * 40)
    
    if build_exe():
        print("\n🎉 빌드 완료!")
        print("dist/SmartAssistant.exe 파일을 실행해보세요.")
    else:
        print("\n❌ 빌드 실패!")
        print("오류를 확인하고 다시 시도해주세요.")

# -*- coding: utf-8 -*-
"""
PyInstaller를 사용하여 exe 파일 생성
"""
import os
import subprocess
import sys
from pathlib import Path

def build_exe():
    """exe 파일 빌드"""
    print("🔨 Smart Assistant exe 파일 빌드 시작...")
    
    # PyInstaller 설치 확인
    try:
        import PyInstaller
        print("✅ PyInstaller가 설치되어 있습니다.")
    except ImportError:
        print("❌ PyInstaller가 설치되지 않았습니다. 설치 중...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        print("✅ PyInstaller 설치 완료")
    
    # 빌드 명령어 구성
    build_command = [
        "pyinstaller",
        "--onefile",  # 단일 exe 파일 생성
        "--windowed",  # 콘솔 창 숨기기
        "--name=SmartAssistant",  # exe 파일명
        "--icon=icon.ico",  # 아이콘 파일 (있는 경우)
        "--add-data=config;config",  # 설정 파일 포함
        "--add-data=sample_messages.json;.",  # 샘플 데이터 포함
        "--hidden-import=PyQt6",
        "--hidden-import=PyQt6.QtCore",
        "--hidden-import=PyQt6.QtWidgets",
        "--hidden-import=PyQt6.QtGui",
        "--hidden-import=asyncio",
        "--hidden-import=imaplib",
        "--hidden-import=email",
        "run_gui.py"  # 메인 스크립트
    ]
    
    # 아이콘 파일이 없으면 해당 옵션 제거
    if not os.path.exists("icon.ico"):
        build_command = [cmd for cmd in build_command if not cmd.startswith("--icon")]
    
    print("🔨 빌드 명령어:", " ".join(build_command))
    
    try:
        # 빌드 실행
        subprocess.check_call(build_command)
        print("✅ exe 파일 빌드 완료!")
        print("📁 dist/SmartAssistant.exe 파일을 확인하세요.")
        
        # 빌드 결과 확인
        exe_path = Path("dist/SmartAssistant.exe")
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            print(f"📊 파일 크기: {size_mb:.1f} MB")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ 빌드 실패: {e}")
        return False
    
    return True

def create_icon():
    """간단한 아이콘 파일 생성 (선택사항)"""
    try:
        from PIL import Image, ImageDraw, ImageFont
        
        # 64x64 아이콘 생성
        img = Image.new('RGBA', (64, 64), (76, 175, 80, 255))  # 녹색 배경
        draw = ImageDraw.Draw(img)
        
        # 간단한 텍스트 그리기
        try:
            font = ImageFont.truetype("arial.ttf", 20)
        except:
            font = ImageFont.load_default()
        
        draw.text((15, 20), "SA", fill=(255, 255, 255, 255), font=font)
        
        # ICO 파일로 저장
        img.save("icon.ico", format='ICO', sizes=[(64, 64)])
        print("✅ 아이콘 파일 생성 완료: icon.ico")
        
    except ImportError:
        print("⚠️ PIL이 설치되지 않아 아이콘을 생성할 수 없습니다.")
    except Exception as e:
        print(f"⚠️ 아이콘 생성 실패: {e}")

if __name__ == "__main__":
    print("Smart Assistant exe 빌드 도구")
    print("=" * 40)
    
    # 아이콘 생성 시도
    create_icon()
    
    # exe 빌드
    if build_exe():
        print("\n🎉 빌드 완료!")
        print("dist/SmartAssistant.exe 파일을 실행해보세요.")
    else:
        print("\n❌ 빌드 실패!")
        print("오류를 확인하고 다시 시도해주세요.")

"""안건(Agenda) 로더 테스트"""
import pytest
import tempfile
import os
from doorae.core.agenda import load_agendas


def test_load_agendas_success():
    """정상적인 안건 로딩 테스트"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False, encoding='utf-8') as f:
        f.write("""agendas:
  - title: "회의 시작"
    description: "회의를 시작합니다"
    required_speakers: ["Host", "PM"]
  - title: "이슈 논의"
    description: "이슈를 논의합니다"
    required_speakers: ["TechLead"]
""")
        temp_path = f.name

    try:
        agendas = load_agendas(temp_path)
        assert len(agendas) == 2
        assert agendas[0]["title"] == "회의 시작"
        assert agendas[0]["description"] == "회의를 시작합니다"
        assert agendas[0]["required_speakers"] == ["Host", "PM"]
        assert agendas[1]["title"] == "이슈 논의"
        assert agendas[1]["required_speakers"] == ["TechLead"]
    finally:
        os.unlink(temp_path)


def test_load_agendas_empty():
    """빈 파일 테스트"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False, encoding='utf-8') as f:
        f.write("")
        temp_path = f.name

    try:
        agendas = load_agendas(temp_path)
        assert agendas == []
    finally:
        os.unlink(temp_path)


def test_load_agendas_no_agendas_key():
    """agendas 키가 없는 경우 테스트"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False, encoding='utf-8') as f:
        f.write("other_key: value")
        temp_path = f.name

    try:
        agendas = load_agendas(temp_path)
        assert agendas == []
    finally:
        os.unlink(temp_path)


def test_load_agendas_required_fields():
    """필수 필드 확인 테스트"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False, encoding='utf-8') as f:
        f.write("""agendas:
  - title: "테스트 안건"
    description: "테스트 설명"
    required_speakers: ["Host"]
""")
        temp_path = f.name

    try:
        agendas = load_agendas(temp_path)
        assert len(agendas) == 1
        agenda = agendas[0]
        assert "title" in agenda
        assert "description" in agenda
        assert "required_speakers" in agenda
        # status, start_time 등 런타임 필드는 YAML에 없어야 함
        assert "status" not in agenda
        assert "start_time" not in agenda
    finally:
        os.unlink(temp_path)

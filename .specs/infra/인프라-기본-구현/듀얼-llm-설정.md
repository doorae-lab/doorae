# 듀얼 LLM 설정 (Main/Task)

- 상위: [인프라 기본 구현](./__init__.md) - 인프라 핵심 컴포넌트 구현
- 상태: done
- 작성일: 2026-02-10

## 개요

Main LLM (대화용, 고품질) + Task LLM (분석용, 저비용) 이중 구조. Pydantic Settings 기반 환경변수 관리, fallback 체인 지원.

## 관련 코드

- `doorae/config/settings.py`
- `doorae/config/llm_factory.py`

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any

import httpx
import streamlit as st


@dataclass(frozen=True)
class ApiResponse:
    method: str
    url: str
    request_headers: dict[str, str]
    request_json: Any | None
    status_code: int | None
    response_headers: dict[str, str] | None
    response_text: str | None
    response_json: Any | None
    elapsed_ms: int | None
    error: str | None = None


@dataclass(frozen=True)
class Api:
    base_url: str

    def _url(self, path: str) -> str:
        return self.base_url.rstrip("/") + path

    def request(
        self,
        method: str,
        path: str,
        *,
        json_payload: Any | None = None,
        headers: dict[str, str] | None = None,
        timeout_s: int = 120,
    ) -> ApiResponse:
        method_u = method.upper().strip()
        url = self._url(path)
        req_headers = {**(headers or {})}

        started = time.time()
        try:
            r = httpx.request(method_u, url, json=json_payload, headers=req_headers, timeout=timeout_s)
            elapsed_ms = int((time.time() - started) * 1000)
            content_type = (r.headers.get("content-type") or "").lower()
            parsed_json = None
            if "application/json" in content_type:
                try:
                    parsed_json = r.json()
                except Exception:
                    parsed_json = None
            return ApiResponse(
                method=method_u,
                url=url,
                request_headers=req_headers,
                request_json=json_payload,
                status_code=r.status_code,
                response_headers=dict(r.headers),
                response_text=r.text,
                response_json=parsed_json,
                elapsed_ms=elapsed_ms,
                error=None,
            )
        except Exception as e:
            elapsed_ms = int((time.time() - started) * 1000)
            return ApiResponse(
                method=method_u,
                url=url,
                request_headers=req_headers,
                request_json=json_payload,
                status_code=None,
                response_headers=None,
                response_text=None,
                response_json=None,
                elapsed_ms=elapsed_ms,
                error=str(e),
            )


def _json_area(label: str, value: Any) -> None:
    st.subheader(label)
    st.code(json.dumps(value, indent=2, ensure_ascii=False), language="json")


def _safe_json_dumps(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), indent=2)


def _curl_powershell(method: str, url: str, headers: dict[str, str], payload: Any | None) -> str:
    # Designed to be pasted into PowerShell. Uses backticks for line continuation.
    lines: list[str] = [f'curl -X {method.upper()} "{url}"']
    for k, v in headers.items():
        lines.append(f'  -H "{k}: {v}"')
    if payload is not None and method.upper() in {"POST", "PUT", "PATCH"}:
        body = _safe_json_dumps(payload).replace("'", "''")
        lines.append(f"  -d '{body}'")
    return " `\n".join(lines)


def _render_request_details(*, method: str, url: str, headers: dict[str, str], payload: Any | None) -> None:
    st.markdown("#### Request details")
    c1, c2 = st.columns([2, 1])
    with c1:
        st.caption("URL")
        st.code(url)
        st.caption("JSON body")
        st.code(_safe_json_dumps(payload) if payload is not None else "(no body)", language="json")
    with c2:
        st.caption("Method")
        st.code(method.upper())
        st.caption("Headers")
        st.code(_safe_json_dumps(headers), language="json")

    st.caption("PowerShell curl")
    st.code(_curl_powershell(method, url, headers, payload), language="powershell")


def _normalize_console_path(raw: str) -> str:
    """
    Accept common paste formats like:
      - /api/v1/versions/proj_1
      - GET /api/v1/versions/proj_1
    and return a clean path. If a full URL is provided, return it unchanged.
    """
    s = (raw or "").strip()
    if not s:
        return s
    if s.startswith("http://") or s.startswith("https://"):
        return s
    for verb in ("GET", "POST", "PUT", "PATCH", "DELETE"):
        prefix = verb + " "
        if s.upper().startswith(prefix):
            s = s[len(prefix) :].strip()
            break
    # Streamlit input sometimes includes accidental leading/trailing quotes.
    s = s.strip("\"'")
    if not s.startswith("/"):
        s = "/" + s
    return s


def _render_response(resp: ApiResponse) -> None:
    st.markdown("#### Response")
    if resp.error:
        st.error(resp.error)
        return

    meta = f"HTTP {resp.status_code} • {resp.elapsed_ms}ms"
    if resp.status_code is not None and 200 <= resp.status_code < 300:
        st.success(meta)
    else:
        st.warning(meta)

    if resp.response_json is not None:
        st.code(json.dumps(resp.response_json, indent=2, ensure_ascii=False), language="json")
    else:
        st.code(resp.response_text or "")


def _is_success(resp: ApiResponse) -> bool:
    return resp.error is None and resp.status_code is not None and 200 <= resp.status_code < 300


def _try_parse_jsonish(text: str) -> Any | None:
    """
    Try to parse strings that may be:
    - raw JSON text
    - JSON-stringified JSON (double-encoded)
    - "JSON-ish" where quotes are backslash-escaped (e.g. {\"k\": \"v\"})
    """
    s0 = (text or "").strip()
    if not s0:
        return None

    candidates: list[str] = [s0]
    if (s0.startswith('"') and s0.endswith('"')) or (s0.startswith("'") and s0.endswith("'")):
        candidates.append(s0[1:-1].strip())
    # Common double-escaped JSON produced by serializing JSON into a text field.
    candidates.append(s0.replace('\\"', '"').replace("\\n", "\n"))

    for s in candidates:
        try:
            v = json.loads(s)
        except Exception:
            continue
        if isinstance(v, str):
            # If we decoded into a JSON string, try one more time.
            try:
                return json.loads(v)
            except Exception:
                return v
        return v
    return None


def _render_latest_version_pretty(version_entity: dict[str, Any]) -> None:
    st.markdown("#### Latest version")
    ver = version_entity.get("version_number")
    vid = version_entity.get("version_id")
    if ver is not None:
        st.caption(f"version_number: {ver}" + (f" • version_id: {vid}" if vid else ""))

    content = version_entity.get("content") or ""
    tab_rendered, tab_raw = st.tabs(["Rendered", "Raw"])
    with tab_rendered:
        st.markdown(content if isinstance(content, str) else str(content))
    with tab_raw:
        st.code(content if isinstance(content, str) else _safe_json_dumps(content))


def _render_versions_list_pretty(payload: dict[str, Any]) -> None:
    st.markdown("#### Versions")
    versions = payload.get("versions") or []
    if not isinstance(versions, list) or not versions:
        st.caption("No versions found for project.")
        return

    # Build a stable view of versions
    versions_sorted = sorted(
        [v for v in versions if isinstance(v, dict)],
        key=lambda v: int(v.get("version_number") or 0),
    )
    latest = versions_sorted[-1]

    tab_latest, tab_select, tab_all, tab_table, tab_raw = st.tabs(["Latest", "Select", "All (scroll)", "Table", "Raw"])

    with tab_latest:
        _render_latest_version_pretty(latest)

    with tab_select:
        def _label(v: dict[str, Any]) -> str:
            vn = v.get("version_number")
            kind = v.get("version_kind")
            lbl = v.get("variant_label")
            parts = [f"v{vn}", str(kind or "")]
            if lbl:
                parts.append(str(lbl))
            return " • ".join([p for p in parts if p])

        indices = list(range(len(versions_sorted)))
        default_idx = max(0, len(indices) - 1)
        chosen_idx = st.selectbox(
            "version",
            options=indices,
            index=default_idx,
            format_func=lambda i: _label(versions_sorted[i]),
        )
        chosen_entity = versions_sorted[int(chosen_idx)]
        _render_latest_version_pretty(chosen_entity)

    with tab_all:
        st.caption("Showing newest first. Expand a version to view its full content.")
        newest_first = list(reversed(versions_sorted))
        for v in newest_first:
            vn = v.get("version_number")
            kind = v.get("version_kind")
            lbl = v.get("variant_label")
            vid = v.get("version_id")
            header = f"v{vn} • {kind}" + (f" • {lbl}" if lbl else "")
            with st.expander(header, expanded=False):
                if vid:
                    st.caption(f"version_id: {vid}")
                content = v.get("content") or ""
                t_render, t_raw2 = st.tabs(["Rendered", "Raw"])
                with t_render:
                    st.markdown(content if isinstance(content, str) else str(content))
                with t_raw2:
                    st.code(content if isinstance(content, str) else _safe_json_dumps(content))

    with tab_table:
        rows = [
            {
                "version_number": int(v.get("version_number") or 0),
                "version_kind": v.get("version_kind"),
                "variant_label": v.get("variant_label"),
                "version_id": v.get("version_id"),
                "content_preview": (v.get("content") or "")[:200].replace("\n", " "),
            }
            for v in versions_sorted
        ]
        st.dataframe(rows, use_container_width=True)

    with tab_raw:
        st.code(_safe_json_dumps(payload), language="json")


def _extract_preview_text(obj: Any) -> str | None:
    if isinstance(obj, str):
        return obj
    if not isinstance(obj, dict):
        return None
    # Unwrap { "linkedin_post": {...} } etc.
    if len(obj) == 1:
        k = next(iter(obj.keys()))
        v = obj.get(k)
        if isinstance(v, dict):
            obj = v
    for key in ("body", "text", "content", "markdown"):
        v = obj.get(key)
        if isinstance(v, str) and v.strip():
            return v
    return None


def _render_platform_outputs_pretty(payload: dict[str, Any]) -> None:
    st.markdown("#### Platform outputs")
    outputs = payload.get("outputs") or []
    if not isinstance(outputs, list) or not outputs:
        st.caption("No platform outputs found.")
        return

    # Sort for stable tab order.
    outputs_sorted = sorted(outputs, key=lambda o: str((o or {}).get("platform") or ""))
    labels = []
    for o in outputs_sorted:
        plat = (o or {}).get("platform") or "unknown"
        opt = (o or {}).get("optimized")
        labels.append(f"{plat}{' ✓' if opt else ''}")

    tabs = st.tabs(labels)
    for idx, o in enumerate(outputs_sorted):
        o = o or {}
        with tabs[idx]:
            plat = o.get("platform") or "unknown"
            st.caption(f"platform: {plat} • format_type: {o.get('format_type')} • optimized: {o.get('optimized')}")

            raw_content = o.get("content")
            parsed = _try_parse_jsonish(raw_content) if isinstance(raw_content, str) else raw_content

            preview = _extract_preview_text(parsed)
            t_preview, t_raw = st.tabs(["Preview", "Raw"])
            with t_preview:
                if preview:
                    st.markdown(preview)
                else:
                    st.caption("No obvious preview field found; showing raw content below.")
                    st.code(raw_content if isinstance(raw_content, str) else _safe_json_dumps(raw_content))
            with t_raw:
                if isinstance(parsed, (dict, list)):
                    st.code(_safe_json_dumps(parsed), language="json")
                else:
                    st.code(raw_content if isinstance(raw_content, str) else _safe_json_dumps(raw_content))


def _push_history(resp: ApiResponse) -> None:
    st.session_state.setdefault("api_history", [])
    st.session_state["api_history"].append(
        {
            "method": resp.method,
            "url": resp.url,
            "status": resp.status_code,
            "elapsed_ms": resp.elapsed_ms,
            "request_json": resp.request_json,
            "error": resp.error,
        }
    )


def main() -> None:
    st.set_page_config(page_title="CPublishr Backend Tester", layout="wide")
    st.title("CPublishr Backend Tester (Streamlit)")

    with st.sidebar:
        base_url = st.text_input("Backend base URL", value="http://127.0.0.1:8010")
        project_id = st.text_input("Project ID", value=st.session_state.get("project_id", "proj_local_1"))
        st.session_state["project_id"] = project_id
        st.session_state.setdefault("editorial_session_id", "")

        st.divider()
        show_details = st.checkbox("Show request details (for every call)", value=True)
        default_timeout_s = st.number_input("Timeout seconds", min_value=5, value=120, step=5)

        st.divider()
        st.caption("Tip: run backend with `uvicorn src.main:app --reload --port 8000`")

    api = Api(base_url=base_url)

    tab_flow, tab_console, tab_storage, tab_publish, tab_health = st.tabs(
        ["Curl-aligned Test Flow", "API Console", "Storage (Versions/Outputs)", "Publishing", "Health"]
    )

    with tab_flow:
        st.markdown(
            """
This tab mirrors your PowerShell curl flow and shows **method / URL / headers / JSON body** for every call.
"""
        )

        default_headers = {"Content-Type": "application/json"}

        st.markdown("### 0) Health check (`GET /healthz`)")
        if st.button("Run: GET /healthz"):
            resp = api.request("GET", "/healthz", headers={}, timeout_s=int(default_timeout_s))
            if show_details:
                with st.expander("Request details", expanded=True):
                    _render_request_details(method=resp.method, url=resp.url, headers=resp.request_headers, payload=None)
            _render_response(resp)
            _push_history(resp)

        st.divider()
        st.markdown("### 1) Initialize project (Node 0) (`POST /api/v1/projects/`)")
        with st.form("flow_node0"):
            topic_title = st.text_input("topic_title", value="AI Multi-Agent Content")
            core_idea = st.text_area("core_idea", value="One master doc, many platform outputs", height=80)
            user_content = st.text_area(
                "user_content (optional)",
                value=(
                    "Imagine your content as a movie script: you write one master doc, and a crew of AI "
                    '"agents" turns it into trailers, posters, and behind-the-scenes clips-automatically. '
                    "One agent makes a punchy LinkedIn post, another crafts an Instagram carousel, a third "
                    "writes a Twitter/X thread, and a fourth adapts it into a YouTube short script. Same core "
                    "story, different costumes, different stage. The fun part? You stop rewriting from scratch "
                    'and start "directing" the message-while your agents handle the platform-specific polish.'
                ),
                height=80,
            )
            target_audience_opt = st.selectbox(
                "target_audience (optional)",
                ["(none)", "builders", "founders", "enterprise", "general tech"],
                index=1,
            )
            content_depth_opt = st.selectbox(
                "content_depth (optional)",
                ["(none)", "surface", "intermediate", "deep"],
                index=2,
            )
            tone_preference = st.selectbox(
                "tone_preference",
                ["professional", "analytical", "conversational"],
                index=0,
            )
            distribution_targets = st.multiselect(
                "distribution_targets",
                ["linkedin", "x", "medium", "github", "youtube", "instagram", "substack"],
                default=["linkedin", "x", "medium", "github"],
            )
            submitted0 = st.form_submit_button("POST /api/v1/projects/")

        target_audience = None if target_audience_opt == "(none)" else target_audience_opt
        content_depth = None if content_depth_opt == "(none)" else content_depth_opt
        topic_payload_current = {
            "project_id": project_id,
            "topic_title": topic_title,
            "core_idea": core_idea,
            "user_content": (user_content or None),
            "target_audience": target_audience,
            "content_depth": content_depth,
            "tone_preference": tone_preference,
            "distribution_targets": distribution_targets,
        }

        if submitted0:
            if not distribution_targets:
                st.error("distribution_targets must include at least one platform.")
                st.stop()
            payload0 = topic_payload_current
            resp = api.request(
                "POST",
                "/api/v1/projects/",
                json_payload=payload0,
                headers=default_headers,
                timeout_s=int(default_timeout_s),
            )
            if show_details:
                with st.expander("Request details", expanded=True):
                    _render_request_details(method=resp.method, url=resp.url, headers=resp.request_headers, payload=payload0)
            _render_response(resp)
            _push_history(resp)

        st.divider()
        st.markdown("### 1a) Run research only (`POST /api/v1/workflows/nodes/research`)")
        persist_context_research = st.checkbox("persist_context (research)", value=True)
        if st.button("POST /api/v1/workflows/nodes/research"):
            if not topic_payload_current.get("distribution_targets"):
                st.error("distribution_targets must include at least one platform.")
                st.stop()
            payload_research = {
                "topic": topic_payload_current,
                "persist_context": bool(persist_context_research),
            }
            resp = api.request(
                "POST",
                "/api/v1/workflows/nodes/research",
                json_payload=payload_research,
                headers=default_headers,
                timeout_s=int(default_timeout_s),
            )
            if show_details:
                with st.expander("Request details", expanded=True):
                    _render_request_details(
                        method=resp.method,
                        url=resp.url,
                        headers=resp.request_headers,
                        payload=payload_research,
                    )
            _render_response(resp)
            _push_history(resp)

        st.divider()
        st.markdown("### 1b) Run master only (`POST /api/v1/workflows/nodes/master`)")
        c_m1, c_m2 = st.columns(2)
        with c_m1:
            persist_context_master = st.checkbox("persist_context (master)", value=True)
        with c_m2:
            persist_versions_master = st.checkbox("persist_versions (master)", value=True)
        research_override_raw = st.text_area(
            "research override (optional JSON)",
            value="",
            help="Optional `ResearchTrendResponse` JSON. Leave blank to auto-run Node 1 inside this endpoint.",
            height=120,
        )
        if st.button("POST /api/v1/workflows/nodes/master"):
            if not topic_payload_current.get("distribution_targets"):
                st.error("distribution_targets must include at least one platform.")
                st.stop()
            payload_master: dict[str, Any] = {
                "topic": topic_payload_current,
                "persist_context": bool(persist_context_master),
                "persist_versions": bool(persist_versions_master),
            }
            if research_override_raw.strip():
                try:
                    payload_master["research"] = json.loads(research_override_raw)
                except Exception as e:
                    st.error(f"Invalid research override JSON: {e}")
                    st.stop()

            resp = api.request(
                "POST",
                "/api/v1/workflows/nodes/master",
                json_payload=payload_master,
                headers=default_headers,
                timeout_s=int(default_timeout_s),
            )
            if show_details:
                with st.expander("Request details", expanded=True):
                    _render_request_details(
                        method=resp.method,
                        url=resp.url,
                        headers=resp.request_headers,
                        payload=payload_master,
                    )
            _render_response(resp)
            _push_history(resp)

        st.divider()
        st.markdown("### 2) Run workflow (`POST /api/v1/workflows/runs`)")
        c_run1, c_run2 = st.columns([1, 2])
        with c_run1:
            run_editorial = st.checkbox("run_editorial", value=True)
        with c_run2:
            editorial_comment = st.text_input("editorial_comment (optional)", value="")

        payload_run = {
            "project_id": project_id,
            "run_editorial": bool(run_editorial),
            "editorial_comment": (editorial_comment or None),
        }
        if st.button("POST /api/v1/workflows/runs"):
            resp = api.request(
                "POST",
                "/api/v1/workflows/runs",
                json_payload=payload_run,
                headers=default_headers,
                timeout_s=int(default_timeout_s),
            )
            if show_details:
                with st.expander("Request details", expanded=True):
                    _render_request_details(method=resp.method, url=resp.url, headers=resp.request_headers, payload=payload_run)
            _render_response(resp)
            _push_history(resp)

        with st.expander("Other backend endpoints (direct)", expanded=False):
            st.caption("These are also available in the backend OpenAPI; useful for quick spot-checks.")

            c_a, c_b = st.columns(2)
            with c_a:
                if st.button("GET /api/v1/projects/{project_id}"):
                    resp = api.request("GET", f"/api/v1/projects/{project_id}", headers={}, timeout_s=int(default_timeout_s))
                    if show_details:
                        with st.expander("Request details", expanded=True):
                            _render_request_details(method=resp.method, url=resp.url, headers=resp.request_headers, payload=None)
                    _render_response(resp)
                    _push_history(resp)

                if st.button("GET /api/v1/workflows/nodes/research/{project_id}"):
                    resp = api.request(
                        "GET", f"/api/v1/workflows/nodes/research/{project_id}", headers={}, timeout_s=int(default_timeout_s)
                    )
                    if show_details:
                        with st.expander("Request details", expanded=True):
                            _render_request_details(method=resp.method, url=resp.url, headers=resp.request_headers, payload=None)
                    _render_response(resp)
                    _push_history(resp)

            with c_b:
                if st.button("GET /api/v1/workflows/nodes/master/{project_id}"):
                    resp = api.request(
                        "GET", f"/api/v1/workflows/nodes/master/{project_id}", headers={}, timeout_s=int(default_timeout_s)
                    )
                    if show_details:
                        with st.expander("Request details", expanded=True):
                            _render_request_details(method=resp.method, url=resp.url, headers=resp.request_headers, payload=None)
                    _render_response(resp)
                    _push_history(resp)

                st.markdown("#### POST /api/v1/workflows/nodes/editorial")
                with st.form("editorial_direct"):
                    current_version_direct = st.number_input("current_version (direct)", min_value=1, value=1, step=1)
                    user_feedback_direct = st.text_area(
                        "user_feedback (direct)", value="Make it simpler for beginners", height=80
                    )
                    action_direct = st.selectbox(
                        "action (direct)",
                        ["rewrite", "expand", "shorten", "simplify", "optimize"],
                        index=0,
                    )
                    target_section_direct = st.text_input("target_section (direct)", value="document")
                    submit_direct = st.form_submit_button("Run direct editorial")

                if submit_direct:
                    payload_direct = {
                        "project_id": project_id,
                        "current_version": int(current_version_direct),
                        "editor_actions": [{"action": action_direct, "target_section": target_section_direct}],
                        "user_feedback": user_feedback_direct,
                    }
                    resp = api.request(
                        "POST",
                        "/api/v1/workflows/nodes/editorial",
                        json_payload=payload_direct,
                        headers=default_headers,
                        timeout_s=int(default_timeout_s),
                    )
                    if show_details:
                        with st.expander("Request details", expanded=True):
                            _render_request_details(
                                method=resp.method, url=resp.url, headers=resp.request_headers, payload=payload_direct
                            )
                    _render_response(resp)
                    _push_history(resp)

        st.divider()
        st.markdown("### 3) Editorial workflow (session-based)")

        st.markdown("#### 3a) Start session (`POST /api/v1/workflows/nodes/editorial/session/start`)")
        with st.form("editorial_start"):
            current_version = st.number_input("current_version", min_value=1, value=1, step=1)
            user_comment_start = st.text_area("user_comment", value="Make it simpler for beginners", height=80)
            start_submit = st.form_submit_button("Start session")

        if start_submit:
            payload_start = {
                "project_id": project_id,
                "current_version": int(current_version),
                "user_comment": user_comment_start,
            }
            resp = api.request(
                "POST",
                "/api/v1/workflows/nodes/editorial/session/start",
                json_payload=payload_start,
                headers=default_headers,
                timeout_s=int(default_timeout_s),
            )
            if show_details:
                with st.expander("Request details", expanded=True):
                    _render_request_details(
                        method=resp.method, url=resp.url, headers=resp.request_headers, payload=payload_start
                    )
            _render_response(resp)
            _push_history(resp)
            if resp.response_json and isinstance(resp.response_json, dict) and resp.response_json.get("session_id"):
                st.session_state["editorial_session_id"] = resp.response_json["session_id"]

        st.markdown("#### 3b) Iterate (`POST /api/v1/workflows/nodes/editorial/session/{session_id}/iterate`)")
        session_id = st.text_input(
            "session_id",
            value=st.session_state.get("editorial_session_id", ""),
            help="Auto-filled after Start Session if the API returned session_id.",
        )
        st.session_state["editorial_session_id"] = session_id
        with st.form("editorial_iterate"):
            user_comment_iter = st.text_area("user_comment (iterate)", value="Add one concrete example", height=80)
            iter_submit = st.form_submit_button("Iterate session")

        if iter_submit:
            if not session_id.strip():
                st.error("session_id is required. Start a session first (step 3a) or paste an existing session_id.")
            else:
                payload_iter = {"user_comment": user_comment_iter}
                path = f"/api/v1/workflows/nodes/editorial/session/{session_id}/iterate"
                resp = api.request(
                    "POST",
                    path,
                    json_payload=payload_iter,
                    headers=default_headers,
                    timeout_s=int(default_timeout_s),
                )
                if show_details:
                    with st.expander("Request details", expanded=True):
                        _render_request_details(
                            method=resp.method, url=resp.url, headers=resp.request_headers, payload=payload_iter
                        )
                _render_response(resp)
                _push_history(resp)

        st.markdown("#### 3c) Finalize (`POST /api/v1/workflows/nodes/editorial/session/{session_id}/finalize`)")
        if st.button("Finalize session"):
            if not session_id.strip():
                st.error("session_id is required. Start a session first (step 3a) or paste an existing session_id.")
            else:
                path = f"/api/v1/workflows/nodes/editorial/session/{session_id}/finalize"
                resp = api.request(
                    "POST",
                    path,
                    json_payload=None,
                    headers=default_headers,
                    timeout_s=int(default_timeout_s),
                )
                if show_details:
                    with st.expander("Request details", expanded=True):
                        _render_request_details(method=resp.method, url=resp.url, headers=resp.request_headers, payload=None)
                _render_response(resp)
                _push_history(resp)

        st.divider()
        st.markdown("### 4) Verify outputs (`GET /api/v1/versions/{project_id}` and `GET /api/v1/platform-outputs/{project_id}`)")
        c_v, c_o = st.columns(2)
        with c_v:
            version_kind = st.selectbox(
                "version_kind (optional filter)",
                ["all", "base", "variant", "editorial"],
                index=0,
                key="verify_version_kind",
            )
            versions_path = (
                f"/api/v1/versions/{project_id}" if version_kind == "all" else f"/api/v1/versions/{project_id}/{version_kind}"
            )
            if st.button("GET versions"):
                resp = api.request("GET", versions_path, headers={}, timeout_s=int(default_timeout_s))
                if show_details:
                    with st.expander("Request details", expanded=True):
                        _render_request_details(method=resp.method, url=resp.url, headers=resp.request_headers, payload=None)
                if _is_success(resp) and isinstance(resp.response_json, dict):
                    _render_versions_list_pretty(resp.response_json)
                    with st.expander("Raw response", expanded=False):
                        _render_response(resp)
                else:
                    _render_response(resp)
                _push_history(resp)
        with c_o:
            if st.button("GET /api/v1/platform-outputs/{project_id}"):
                resp = api.request(
                    "GET", f"/api/v1/platform-outputs/{project_id}", headers={}, timeout_s=int(default_timeout_s)
                )
                if show_details:
                    with st.expander("Request details", expanded=True):
                        _render_request_details(method=resp.method, url=resp.url, headers=resp.request_headers, payload=None)
                if _is_success(resp) and isinstance(resp.response_json, dict):
                    _render_platform_outputs_pretty(resp.response_json)
                    with st.expander("Raw response", expanded=False):
                        _render_response(resp)
                else:
                    _render_response(resp)
                _push_history(resp)

        st.divider()
        st.markdown("### 5) Test publish stub (`POST /api/v1/publishing/jobs`)")
        with st.form("flow_publish"):
            platform = st.selectbox("platform", ["linkedin", "x", "medium", "github", "youtube", "instagram", "substack"], index=0)
            scheduled_time = st.text_input("scheduled_time (ISO-8601 or blank)", value="")
            pub_submit = st.form_submit_button("Create publish job")

        if pub_submit:
            payload_pub = {
                "platform": platform,
                "content_payload": {"project_id": project_id},
                "scheduled_time": scheduled_time or None,
            }
            resp = api.request(
                "POST",
                "/api/v1/publishing/jobs",
                json_payload=payload_pub,
                headers=default_headers,
                timeout_s=int(default_timeout_s),
            )
            if show_details:
                with st.expander("Request details", expanded=True):
                    _render_request_details(method=resp.method, url=resp.url, headers=resp.request_headers, payload=payload_pub)
            _render_response(resp)
            _push_history(resp)

        with st.expander("Request history (this UI session)", expanded=False):
            hist = st.session_state.get("api_history", [])
            if not hist:
                st.caption("No requests yet.")
            else:
                st.dataframe(hist, use_container_width=True)

    with tab_console:
        st.markdown("### API Console")
        st.caption("Build and send any GET/POST request, with request details shown exactly like your curl flow.")

        method = st.selectbox("method", ["GET", "POST", "PUT", "PATCH", "DELETE"], index=0)
        path_raw = st.text_input("path", value="/api/v1/projects/")
        path = _normalize_console_path(path_raw)
        if path_raw.strip() != path.strip():
            st.caption(f"Normalized path → `{path}`")
        headers_raw = st.text_area("headers (JSON)", value=json.dumps({"Content-Type": "application/json"}, indent=2), height=100)
        body_raw = st.text_area("body (JSON, optional)", value="", height=160)

        headers_obj: dict[str, str] = {}
        try:
            parsed = json.loads(headers_raw) if headers_raw.strip() else {}
            headers_obj = {str(k): str(v) for k, v in (parsed or {}).items()}
        except Exception as e:
            st.error(f"Invalid headers JSON: {e}")

        json_body: Any | None = None
        if body_raw.strip():
            try:
                json_body = json.loads(body_raw)
            except Exception as e:
                st.error(f"Invalid body JSON: {e}")

        if st.button("Send request"):
            if " " in path and not (path.startswith("http://") or path.startswith("https://")):
                st.error("Path contains spaces. Use a URL path like `/api/v1/versions/proj_1` (not `GET /...`).")
                st.stop()
            resp = api.request(method, path, json_payload=json_body, headers=headers_obj, timeout_s=int(default_timeout_s))
            if show_details:
                with st.expander("Request details", expanded=True):
                    _render_request_details(method=resp.method, url=resp.url, headers=resp.request_headers, payload=json_body)
            _render_response(resp)
            _push_history(resp)

    with tab_storage:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("### Versions")
            version_kind_storage = st.selectbox(
                "version_kind (optional filter)",
                ["all", "base", "variant", "editorial"],
                index=0,
                key="storage_version_kind",
            )
            versions_path_storage = (
                f"/api/v1/versions/{project_id}"
                if version_kind_storage == "all"
                else f"/api/v1/versions/{project_id}/{version_kind_storage}"
            )
            st.caption(f"Endpoint: `{versions_path_storage}`")
            if st.button("Refresh versions"):
                resp = api.request("GET", versions_path_storage, headers={}, timeout_s=int(default_timeout_s))
                if show_details:
                    with st.expander("Request details", expanded=True):
                        _render_request_details(method=resp.method, url=resp.url, headers=resp.request_headers, payload=None)
                if _is_success(resp) and isinstance(resp.response_json, dict):
                    _render_versions_list_pretty(resp.response_json)
                    with st.expander("Raw response", expanded=False):
                        _render_response(resp)
                else:
                    _render_response(resp)
                _push_history(resp)
        with c2:
            st.markdown("### Platform outputs (`GET /api/v1/platform-outputs/{project_id}`)")
            if st.button("Refresh platform outputs"):
                resp = api.request(
                    "GET", f"/api/v1/platform-outputs/{project_id}", headers={}, timeout_s=int(default_timeout_s)
                )
                if show_details:
                    with st.expander("Request details", expanded=True):
                        _render_request_details(method=resp.method, url=resp.url, headers=resp.request_headers, payload=None)
                if _is_success(resp) and isinstance(resp.response_json, dict):
                    _render_platform_outputs_pretty(resp.response_json)
                    with st.expander("Raw response", expanded=False):
                        _render_response(resp)
                else:
                    _render_response(resp)
                _push_history(resp)

    with tab_publish:
        st.markdown("### Create publish job (`POST /api/v1/publishing/jobs`)")
        platform = st.selectbox(
            "platform", ["linkedin", "x", "youtube", "instagram", "substack", "medium", "github"], index=0
        )
        scheduled_time = st.text_input("scheduled_time (ISO-8601 or blank)", value="")
        payload_preview = {
            "platform": platform,
            "content_payload": {"project_id": project_id},
            "scheduled_time": scheduled_time or None,
        }
        st.caption("Request preview")
        st.code(json.dumps(payload_preview, indent=2), language="json")
        if st.button("Create publish job"):
            resp = api.request(
                "POST",
                "/api/v1/publishing/jobs",
                json_payload=payload_preview,
                headers={"Content-Type": "application/json"},
                timeout_s=int(default_timeout_s),
            )
            if show_details:
                with st.expander("Request details", expanded=True):
                    _render_request_details(method=resp.method, url=resp.url, headers=resp.request_headers, payload=payload_preview)
            _render_response(resp)
            _push_history(resp)

    with tab_health:
        c1, c2 = st.columns(2)
        with c1:
            if st.button("GET /healthz (simple)"):
                resp = api.request("GET", "/healthz", headers={}, timeout_s=int(default_timeout_s))
                if show_details:
                    with st.expander("Request details", expanded=True):
                        _render_request_details(method=resp.method, url=resp.url, headers=resp.request_headers, payload=None)
                _render_response(resp)
                _push_history(resp)
        with c2:
            if st.button("GET /api/v1/health/"):
                resp = api.request("GET", "/api/v1/health/", headers={}, timeout_s=int(default_timeout_s))
                if show_details:
                    with st.expander("Request details", expanded=True):
                        _render_request_details(method=resp.method, url=resp.url, headers=resp.request_headers, payload=None)
                _render_response(resp)
                _push_history(resp)


if __name__ == "__main__":
    main()



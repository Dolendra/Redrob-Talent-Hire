# dashboard/components/pool_upload.py
import streamlit as st
import io
import os
import json
import zipfile
import tempfile
from pathlib import Path
import concurrent.futures
from typing import List, Dict, Any, Tuple
from src.pool_manager import PoolManager
from src.ingestion import ProductionIngestionService

ROOT = Path(__file__).resolve().parent.parent.parent

def render_pool_upload(pool_manager: PoolManager, vocab: List[str]):
    st.markdown("<h3>Candidate Pool Loader</h3>", unsafe_allow_html=True)
    st.markdown("<p style='color:#94a3b8; font-size:13px;'>Load a pre-compiled JSONL candidate pool or parse multiple resumes in parallel.</p>", unsafe_allow_html=True)
    
    tab_a, tab_b = st.tabs(["📂 JSONL Candidate Pool", "📤 Resume Folder / ZIP Extractor"])
    
    # Session state initialization
    if "temp_pool_path" not in st.session_state:
        st.session_state.temp_pool_path = None
    if "temp_pool_mtime" not in st.session_state:
        st.session_state.temp_pool_mtime = 0.0
    if "bulk_parse_results" not in st.session_state:
        st.session_state.bulk_parse_results = []
    if "resume_jsonl_bytes" not in st.session_state:
        st.session_state.resume_jsonl_bytes = None
        
    # Tab A: JSONL Pool
    with tab_a:
        st.markdown("<h4>Upload Pre-compiled Candidates Pool</h4>", unsafe_allow_html=True)
        uploaded_pool = st.file_uploader(
            "Drop candidates.jsonl or candidates.jsonl.gz file:",
            type=["jsonl", "gz"],
            key="pool_file_uploader",
            label_visibility="collapsed"
        )
        
        if uploaded_pool:
            if st.button("🚀 Load Pool into Ranker", key="load_pool_btn"):
                # Save file to a temporary location
                temp_dir = Path(tempfile.mkdtemp())
                temp_path = temp_dir / uploaded_pool.name
                with open(temp_path, "wb") as f:
                    f.write(uploaded_pool.getbuffer())
                
                # Streaming load with progress bar
                progress_bar = st.progress(0.0)
                status_text = st.empty()
                
                def progress_cb(pct, msg):
                    progress_bar.progress(pct)
                    status_text.text(msg)
                    
                try:
                    # Load pool using manager
                    list(pool_manager.load_jsonl(temp_path, progress_cb))
                    
                    st.session_state.temp_pool_path = str(temp_path)
                    st.session_state.temp_pool_mtime = os.path.getmtime(temp_path)
                    
                    # Overwrite candidate_pool in state
                    st.session_state.candidate_pool = pool_manager.candidates
                    
                    st.success(f"🎉 Successfully loaded pool from {uploaded_pool.name}!")
                except Exception as e:
                    st.error(f"Failed to load candidate pool: {e}")
                    
        # Preview loaded pool statistics
        if pool_manager.candidates:
            st.markdown("<hr style='border-color:rgba(255,255,255,0.06);'>", unsafe_allow_html=True)
            stats = pool_manager.get_stats()
            
            col_s1, col_s2, col_s3 = st.columns(3)
            with col_s1:
                st.metric("Total Candidates Loaded", stats["total"])
            with col_s2:
                st.metric("Average Experience", f"{stats['average_experience']} years")
            with col_s3:
                st.metric("Errors Detected", stats["errors"])
                
            col_p1, col_p2 = st.columns(2)
            with col_p1:
                st.markdown("<h5>Top Candidate Locations</h5>", unsafe_allow_html=True)
                for loc, count in stats["top_locations"][:5]:
                    st.markdown(f"- **{loc}**: {count} candidates")
            with col_p2:
                st.markdown("<h5>Top Job Titles</h5>", unsafe_allow_html=True)
                for title, count in stats["top_titles"][:5]:
                    st.markdown(f"- **{title}**: {count} candidates")
                    
            st.markdown("<h5>Candidate Pool Preview (First 5 candidates)</h5>", unsafe_allow_html=True)
            st.json(pool_manager.candidates[:5])

    # Tab B: Resume Folder / ZIP Extractor
    with tab_b:
        st.markdown("<h4>Parallel Resume Extractor</h4>", unsafe_allow_html=True)
        uploaded_resumes = st.file_uploader(
            "Upload multiple PDF/DOCX/TXT files or a ZIP archive containing resumes:",
            type=["pdf", "docx", "txt", "zip"],
            accept_multiple_files=True,
            key="resumes_bulk_uploader",
            label_visibility="collapsed"
        )
        
        if uploaded_resumes:
            if st.button("⚡ Parse Resumes in Parallel", key="parse_bulk_btn"):
                st.session_state.bulk_parse_results = []
                
                # Extract ZIP files if any
                all_files: List[Tuple[str, bytes]] = []
                for f in uploaded_resumes:
                    if f.name.endswith(".zip"):
                        try:
                            with zipfile.ZipFile(io.BytesIO(f.read())) as z:
                                for name in z.namelist():
                                    # Ignore directories or system files
                                    if name.endswith("/") or name.startswith("__MACOSX") or name.split("/")[-1].startswith("."):
                                        continue
                                    content = z.read(name)
                                    all_files.append((name.split("/")[-1], content))
                        except Exception as e:
                            st.error(f"Failed to read ZIP archive {f.name}: {e}")
                    else:
                        all_files.append((f.name, f.read()))
                
                if not all_files:
                    st.warning("No files found to process.")
                else:
                    st.info(f"Detected {len(all_files)} resumes. Parsing in progress...")
                    
                    # Parallel resume parsing using ThreadPoolExecutor
                    progress_bar = st.progress(0.0)
                    status_text = st.empty()
                    
                    def process_single_file(file_info: Tuple[str, bytes]) -> Dict[str, Any]:
                        name, content = file_info
                        temp_dir = Path(tempfile.mkdtemp())
                        temp_file = temp_dir / name
                        with open(temp_file, "wb") as f_out:
                            f_out.write(content)
                            
                        result = {
                            "filename": name,
                            "candidate": None,
                            "errors": [],
                            "status": "error"
                        }
                        
                        try:
                            ingestor = ProductionIngestionService(ROOT / "config" / "candidate_schema.json")
                            text = ingestor.extract_document_text(temp_file)
                            
                            features = ingestor.rule_based_ner_normalizer(text, vocab)
                            candidate = ingestor.compile_to_schema_row(features)
                            
                            # Validate
                            errors = pool_manager.validate_candidate(candidate)
                            
                            result["candidate"] = candidate
                            result["errors"] = errors
                            result["status"] = "success" if not errors else "warning"
                        except Exception as e:
                            result["errors"] = [str(e)]
                            
                        # Cleanup temp file
                        if temp_file.exists():
                            try:
                                temp_file.unlink()
                            except Exception:
                                pass
                        return result
                        
                    results = []
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        futures = {executor.submit(process_single_file, f): f for f in all_files}
                        for i, future in enumerate(concurrent.futures.as_completed(futures), 1):
                            res = future.result()
                            results.append(res)
                            progress_bar.progress(i / len(all_files))
                            status_text.text(f"Processed {i}/{len(all_files)}: {res['filename']}")
                            
                    st.session_state.bulk_parse_results = results
                    st.success(f"Parsed {len(all_files)} resumes!")
                    
        # Render Processed Resumes Queue
        if st.session_state.bulk_parse_results:
            st.markdown("<h5>Ingestion Status Queue</h5>", unsafe_allow_html=True)
            
            # Count success vs errors
            success_count = sum(1 for r in st.session_state.bulk_parse_results if r["status"] == "success")
            warn_count = sum(1 for r in st.session_state.bulk_parse_results if r["status"] == "warning")
            err_count = sum(1 for r in st.session_state.bulk_parse_results if r["status"] == "error")
            
            st.markdown(f"""
                <div style="display:flex; gap:16px; margin-bottom:12px; font-family:monospace; font-size:12px;">
                    <span style="color:#22c55e;">● SUCCESS: {success_count}</span>
                    <span style="color:#fbbf24;">● VALIDATION WARN: {warn_count}</span>
                    <span style="color:#ef4444;">● ERROR: {err_count}</span>
                </div>
            """, unsafe_allow_html=True)
            
            # Show a summary table of processing queue
            st.dataframe(
                [
                    {
                        "Filename": r["filename"],
                        "Status": r["status"].upper(),
                        "Errors/Warnings": ", ".join(r["errors"][:2]) if r["errors"] else "None",
                        "Candidate Name": r["candidate"]["profile"]["anonymized_name"] if r["candidate"] else "N/A"
                    }
                    for r in st.session_state.bulk_parse_results
                ],
                use_container_width=True
            )
            
            # Build JSONL compilation for download
            valid_candidates = [r["candidate"] for r in st.session_state.bulk_parse_results if r["candidate"]]
            
            if valid_candidates:
                # Store valid candidates to export path
                jsonl_lines = [json.dumps(c) for c in valid_candidates]
                jsonl_str = "\n".join(jsonl_lines)
                
                col_b1, col_b2 = st.columns(2)
                with col_b1:
                    st.download_button(
                        label="📥 Download Extracted Pool as JSONL",
                        data=jsonl_str,
                        file_name="extracted_candidates.jsonl",
                        mime="application/x-jsonlines",
                        use_container_width=True
                    )
                with col_b2:
                    if st.button("🚀 Load Extracted Pool into Ranker", key="load_extracted_btn"):
                        # Load into pool manager
                        pool_manager.candidates = valid_candidates
                        pool_manager.stats = {
                            "total": len(valid_candidates),
                            "from_jsonl": 0,
                            "from_resume": len(valid_candidates),
                            "errors": warn_count,
                            "error_details": []
                        }
                        
                        # Save to temp file
                        temp_dir = Path(tempfile.mkdtemp())
                        temp_path = temp_dir / "parsed_resumes.jsonl"
                        with open(temp_path, "w", encoding="utf-8") as f:
                            f.write(jsonl_str)
                            
                        st.session_state.temp_pool_path = str(temp_path)
                        st.session_state.temp_pool_mtime = os.path.getmtime(temp_path)
                        st.session_state.candidate_pool = valid_candidates
                        
                        st.success(f"🎉 Loaded {len(valid_candidates)} parsed candidates into ranker workspace!")

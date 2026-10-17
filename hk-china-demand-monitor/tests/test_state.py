from src.state.store import StateStore,classify_change,should_reprocess
def test_state_upsert_is_idempotent(tmp_path):
    store=StateStore(tmp_path/"state.sqlite"); row={"document_id":"x","stock_code":"02020","company_name":"ANTA","industry":"sportswear","financial_year":2024,"report_title":"Annual Report 2024","source_method":"manual","sha256":"abc","content_hash":"def","status":"processed"}; store.upsert_document(row); first=store.get_document("x"); store.upsert_document(row); second=store.get_document("x"); store.close(); assert first["first_seen_at"]==second["first_seen_at"] and second["sha256"]=="abc"
def test_incremental_classification_and_exact_cache(tmp_path):
    old={"sha256":"abc","content_hash":"def"}; assert classify_change(None,"abc","def")=="new"; assert classify_change(old,"abc","def")=="unchanged"; assert classify_change(old,"new","def")=="changed"
    store=StateStore(tmp_path/"cache.sqlite"); store.put_cache("summary:02020","02020",2024,"summary","hash-a","out.json",1.2); assert store.get_cache("summary:02020","hash-a"); assert store.get_cache("summary:02020","hash-b") is None; store.close()
def test_incremental_bootstrap_skip_but_later_markdown_change_reprocesses():
    assert not should_reprocess("new",False,True)
    assert should_reprocess("new",False,False)
    assert should_reprocess("changed",True,True)
    assert not should_reprocess("unchanged",True,True)

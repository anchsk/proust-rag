from search import load_chunk_metadata

def test_load_chunk_metadata(tmp_path):
    csv_file = tmp_path / "fake.csv"
    csv_file.write_text("chunk_id,text\nch1_p1_s0_c0,hello\n")
    result = load_chunk_metadata(str(csv_file))
    assert result["ch1_p1_s0_c0"]["text"] == "hello"

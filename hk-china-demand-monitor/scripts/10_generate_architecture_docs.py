from __future__ import annotations
import re, typer
from _bootstrap import ROOT
from src.common import read_csv, now_iso

def main():
    scripts=sorted(x.name for x in (ROOT/"scripts").glob("[0-9]*.py")); configs=sorted(x.name for x in (ROOT/"config").glob("*")); processed=sorted(x.name for x in (ROOT/"data/processed").glob("*")); web=sorted(x.name for x in (ROOT/"web/public/data").glob("*"))
    generated="<!-- generated:start -->\n## Generated repository inventory\n\n"+f"Refreshed: `{now_iso()}`\n\n- Scripts: {', '.join(scripts)}\n- Config: {', '.join(configs)}\n- Processed data present: {', '.join(processed) or 'none'}\n- Web exports present: {', '.join(web) or 'none'}\n"+"<!-- generated:end -->"
    path=ROOT/"docs/ARCHITECTURE.md"; text=path.read_text(); pattern=r"<!-- generated:start -->.*?<!-- generated:end -->"; text=re.sub(pattern,generated,text,flags=re.S) if re.search(pattern,text,re.S) else text.rstrip()+"\n\n"+generated+"\n"; path.write_text(text); typer.echo(f"Refreshed {path}")
if __name__=="__main__": typer.run(main)


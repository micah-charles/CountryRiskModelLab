from __future__ import annotations
import calendar, typer
from _bootstrap import ROOT

def main(target:str="launchd",weekday:str="monday",time:str="08:00"):
    day=list(calendar.day_name).index(weekday.title())+1; hour,minute=map(int,time.split(":")); ops=ROOT/"ops"; (ops/"logs").mkdir(parents=True,exist_ok=True)
    command=f"cd {ROOT} && {ROOT}/.venv/bin/python scripts/08_incremental_update.py --years 3 --export-web-data"
    if target=="launchd":
        content=f'''<?xml version="1.0" encoding="UTF-8"?><!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd"><plist version="1.0"><dict><key>Label</key><string>com.local.hk-china-demand-monitor.weekly</string><key>ProgramArguments</key><array><string>/bin/zsh</string><string>-lc</string><string>{command}</string></array><key>StartCalendarInterval</key><dict><key>Weekday</key><integer>{day}</integer><key>Hour</key><integer>{hour}</integer><key>Minute</key><integer>{minute}</integer></dict><key>StandardOutPath</key><string>{ops}/logs/weekly_stdout.log</string><key>StandardErrorPath</key><string>{ops}/logs/weekly_stderr.log</string></dict></plist>'''
        path=ops/"launchd/com.local.hk-china-demand-monitor.weekly.plist"; path.parent.mkdir(parents=True,exist_ok=True); path.write_text(content); typer.echo(f"Generated {path}. Load with: launchctl bootstrap gui/$(id -u) {path}")
    elif target=="cron":
        path=ops/"cron.weekly.txt"; path.write_text(f"{minute} {hour} * * {day%7} /bin/zsh -lc '{command}' >> {ops}/logs/weekly_stdout.log 2>> {ops}/logs/weekly_stderr.log\n"); typer.echo(f"Generated {path}; review then install with crontab.")
    else: raise typer.BadParameter("target must be launchd or cron")
if __name__=="__main__": typer.run(main)


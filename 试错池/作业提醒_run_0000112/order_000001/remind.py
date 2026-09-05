#!/usr/bin/env python3
"""
ManageBac 作业与考试提醒工具（最小版）
读取 .ics 文件，生成作业清单、提醒表和群消息
"""

import argparse
import csv
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

try:
    from icalendar import Calendar, Event as ICalEvent
except ImportError:
    print("错误：需要安装 icalendar 库")
    print("请运行: pip install icalendar")
    sys.exit(1)


def parse_ics(ics_path):
    """解析 ICS 文件，返回事件列表"""
    events = []
    
    try:
        with open(ics_path, 'rb') as f:
            cal = Calendar.from_ical(f.read())
    except Exception as e:
        print(f"错误：无法解析 ICS 文件: {e}")
        sys.exit(1)
    
    for component in cal.walk():
        if isinstance(component, ICalEvent):
            # 获取标题
            summary = str(component.get('summary', '无标题'))
            
            # 获取截止时间
            dtstart = component.get('dtstart')
            dtend = component.get('dtend')
            due_date = None
            
            if dtend:
                due_date = dtend.dt
            elif dtstart:
                due_date = dtstart.dt
            
            if isinstance(due_date, datetime):
                due_date = due_date.date()
            
            # 获取科目 - 尝试从多个字段解析
            subject = parse_subject(component, summary)
            
            # 获取创建时间（用于判断是否过期）
            created = component.get('created')
            
            events.append({
                'summary': summary,
                'due_date': due_date,
                'subject': subject,
                'created': created
            })
    
    return events


def parse_subject(component, summary):
    """从各种字段解析科目"""
    # 尝试从 CATEGORIES 获取
    categories = component.get('categories')
    if categories:
        cats = str(categories)
        if cats and cats != 'None' and cats.strip():
            return cats.strip()
    
    # 尝试从描述获取
    description = component.get('description')
    if description:
        desc = str(description)
        # 常见科目关键词
        subjects = ['数学', '语文', '英语', '物理', '化学', '生物', 
                    '历史', '地理', '政治', '音乐', '美术', '体育',
                    '数学', '语文', '英语', '物理', '化学', '生物',
                    'Math', 'English', 'Chinese', 'Physics', 'Chemistry', 'Biology',
                    '历史', '地理', '政治']
        for subj in subjects:
            if subj in desc:
                return subj
    
    # 尝试从标题解析
    subjects = ['数学', '语文', '英语', '物理', '化学', '生物', 
                '历史', '地理', '政治', '音乐', '美术', '体育',
                'Math', 'English', 'Chinese', 'Physics', 'Chemistry', 'Biology']
    for subj in subjects:
        if subj in summary:
            return subj
    
    return '未分类'


def is_expired(due_date):
    """判断事件是否已过期（截止日期在今天之前）"""
    if due_date is None:
        return True
    today = datetime.now().date()
    return due_date < today


def days_until(due_date):
    """计算距离截止日期的天数"""
    if due_date is None:
        return 999
    today = datetime.now().date()
    return (due_date - today).days


def format_date(date_obj):
    """格式化日期为 MM/DD"""
    if date_obj is None:
        return '未知'
    return date_obj.strftime('%m/%d')


def generate_checklist(events, days, output_dir):
    """生成清单.md"""
    future_events = []
    
    for event in events:
        if event['due_date'] is None:
            continue
        days_left = days_until(event['due_date'])
        if 0 <= days_left <= days:
            future_events.append((days_left, event))
    
    # 按截止日期升序排序
    future_events.sort(key=lambda x: (x[0], x[1]['due_date']))
    
    output_path = output_dir / '清单.md'
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('# 作业与考试清单\n\n')
        f.write('| 剩余天数 | 截止日期 | 科目 | 标题 |\n')
        f.write('|---------|---------|------|------|\n')
        
        for days_left, event in future_events:
            due_str = event['due_date'].strftime('%Y-%m-%d')
            subject = event['subject']
            title = event['summary']
            f.write(f"| {days_left} | {due_str} | {subject} | {title} |\n")
    
    print(f"已生成: {output_path}")
    return future_events


def generate_reminder_csv(events, output_dir):
    """生成提醒表.csv"""
    today = datetime.now().date()
    reminders = []
    
    for event in events:
        due_date = event['due_date']
        if due_date is None:
            continue
        
        days_left = days_until(due_date)
        
        # 跳过已过期事件
        if days_left < 0:
            continue
        
        title = event['summary']
        subject = event['subject']
        due_str = due_date.strftime('%Y-%m-%d')
        
        # 生成提前 3 天提醒
        if days_left >= 3:
            remind_date = due_date - timedelta(days=3)
            reminders.append((remind_date, title, subject, due_str, 3))
        
        # 生成提前 1 天提醒
        if days_left >= 1:
            remind_date = due_date - timedelta(days=1)
            reminders.append((remind_date, title, subject, due_str, 1))
        
        # 生成当天提醒（如果还未到截止时间）
        if days_left >= 0:
            # 当天已过的提醒日期可省略，这里保留逻辑但可能不输出
            # 只有当天还没过时才添加
            current_time = datetime.now()
            if due_date == today:
                # 检查是否已过时间（假设截止时间是当天23:59）
                # 为简化，只要当天就添加
                reminders.append((due_date, title, subject, due_str, 0))
    
    # 按提醒日期升序排序
    reminders.sort(key=lambda x: x[0])
    
    output_path = output_dir / '提醒表.csv'
    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['提醒日期', '事件标题', '科目', '截止日期', '剩余天数'])
        
        for remind_date, title, subject, due_str, days_left in reminders:
            writer.writerow([remind_date.strftime('%Y-%m-%d'), title, subject, due_str, days_left])
    
    print(f"已生成: {output_path}")


def generate_group_message(events, output_dir):
    """生成群消息.txt"""
    today = datetime.now().date()
    today_str = today.strftime('%Y-%m-%d')
    
    future_events = []
    for event in events:
        if event['due_date'] is None:
            continue
        days_left = days_until(event['due_date'])
        if 0 <= days_left <= 7:
            future_events.append((days_left, event))
    
    # 按剩余天数升序排序，今天到期的放最前
    future_events.sort(key=lambda x: x[0])
    
    output_path = output_dir / '群消息.txt'
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(f"作业提醒 {today_str} 未来7天\n")
        f.write("=" * 40 + "\n\n")
        
        if not future_events:
            f.write("未来7天暂无作业和考试\n")
        else:
            lines = []
            for days_left, event in future_events:
                subject = event['subject']
                title = event['summary']
                due_str = format_date(event['due_date'])
                
                if days_left == 0:
                    prefix = "【今天】"
                else:
                    prefix = f"剩余{days_left}天"
                
                line = f"{prefix} {subject} {title}（截止 {due_str}）"
                lines.append(line)
            
            # 限制为25行
            if len(lines) > 25:
                for line in lines[:25]:
                    f.write(line + "\n")
                remaining = len(lines) - 25
                f.write(f"\n…还有 {remaining} 项\n")
            else:
                for line in lines:
                    f.write(line + "\n")
    
    print(f"已生成: {output_path}")


def main():
    parser = argparse.ArgumentParser(description='ManageBac 作业与考试提醒工具')
    parser.add_argument('--ics', required=True, help='ICS 文件路径或 URL')
    parser.add_argument('--days', type=int, default=14, help='提前多少天内的作业（默认14天）')
    
    args = parser.parse_args()
    
    ics_path = args.ics
    days = args.days
    
    # 创建输出目录
    output_dir = Path('out')
    output_dir.mkdir(exist_ok=True)
    
    # 解析 ICS 文件
    print(f"正在读取: {ics_path}")
    events = parse_ics(ics_path)
    print(f"共读取到 {len(events)} 个事件")
    
    # 生成各输出文件
    generate_checklist(events, days, output_dir)
    generate_reminder_csv(events, output_dir)
    generate_group_message(events, output_dir)
    
    print("\n完成！输出文件在 out/ 目录下")
    sys.exit(0)


if __name__ == '__main__':
    main()

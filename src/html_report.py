#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
HTML Report Generation Module for Spotify Rediscovery Analyzer
"""

import html
from datetime import datetime
from typing import List, Dict, Tuple, Union


def generate_html_report(
    title: str, 
    params: Dict[str, str], 
    sections: List[Tuple[str, str, List[str], List[Union[Tuple, List]]]]
) -> str:
    """
    Generate a comprehensive HTML report with interactive tables.

    Args:
        title (str): Title of the report
        params (dict): Configuration parameters to display
        sections (list): List of report sections, each containing:
            - section title
            - section subtitle
            - table headers
            - table rows

    Returns:
        str: Complete HTML document
    """
    css = '''
    :root{--bg:#0b0f14;--panel:#121821;--ink:#e8eef6;--muted:#9bb0c9;--accent:#7bdff6;--accent2:#b088f9;--good:#9ae6b4;--warn:#f6ad55;--bad:#feb2b2;}
    *{box-sizing:border-box;font-family:system-ui,-apple-system,Segoe UI,Roboto,Inter,Helvetica,Arial,sans-serif}
    body{margin:0;background:linear-gradient(180deg,#0b0f14,#0d121a);color:var(--ink)}
    header{padding:28px 24px;border-bottom:1px solid #233047;background:radial-gradient(1200px 400px at 10% -10%,#11213544,transparent)}
    h1{margin:0;font-size:28px;letter-spacing:.3px}
    .meta{color:var(--muted);margin-top:6px;font-size:14px}
    .wrap{max-width:1100px;margin:0 auto;padding:22px}
    section{background:var(--panel);border:1px solid #233047;border-radius:16px;margin:18px 0;overflow:hidden;box-shadow:0 10px 30px rgba(0,0,0,.25)}
    section header{display:flex;justify-content:space-between;align-items:baseline;padding:16px 18px;background:linear-gradient(180deg,#121b27,#0f1621);border-bottom:1px solid #233047}
    section h2{margin:0;font-size:18px}
    section p.sub{margin:0;color:var(--muted);font-size:13px}
    .table{width:100%;border-collapse:separate;border-spacing:0}
    .table th,.table td{padding:10px 12px;border-bottom:1px solid #1f2a3a}
    .table th{position:sticky;top:0;background:#0f1621;z-index:1;text-align:left;font-weight:600;color:#c6d4ea}
    .table tr:nth-child(2n){background:#0f1520}
    .table tr:hover{background:#172033}
    .badge{display:inline-block;padding:2px 8px;border-radius:999px;border:1px solid #2a3a53;background:#0f1621;color:#c6d4ea;font-size:12px}
    footer{color:var(--muted);padding:24px;text-align:center}
    .small{font-size:12px;color:var(--muted)}
    .mono{font-family:ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace}
    .right{text-align:right}
    .nowrap{white-space:nowrap}
    .pill{padding:2px 8px;border-radius:999px}
    .ok{background:rgba(154,230,180,.12);border:1px solid rgba(154,230,180,.3)}
    .warn{background:rgba(246,173,85,.12);border:1px solid rgba(246,173,85,.3)}
    .bad{background:rgba(254,178,178,.12);border:1px solid rgba(254,178,178,.3)}
    '''
    js = '''
    // Simple table sort (click a header)
    document.querySelectorAll('table').forEach(t => {
      const ths = t.querySelectorAll('th');
      ths.forEach((th, idx) => {
        th.style.cursor = 'pointer';
        th.addEventListener('click', () => {
          const rows = Array.from(t.querySelectorAll('tbody tr'));
          const asc = th.dataset.sortAsc === 'true' ? false : true;
          th.dataset.sortAsc = asc;
          rows.sort((a,b) => {
            let A = a.children[idx].innerText.trim();
            let B = b.children[idx].innerText.trim();
            const nA = parseFloat(A.replace(/[^0-9.-]/g,''));
            const nB = parseFloat(B.replace(/[^0-9.-]/g,''));
            if (!Number.isNaN(nA) && !Number.isNaN(nB)) { return asc ? nA - nB : nB - nA; }
            return asc ? A.localeCompare(B) : B.localeCompare(A);
          });
          rows.forEach(r => t.querySelector('tbody').appendChild(r));
        });
      });
    });
    '''

    def table_html(headers: List[str], rows: List[Union[Tuple, List]]) -> str:
        """
        Generate HTML for a single table.

        Args:
            headers (list): Table column headers
            rows (list): Table rows

        Returns:
            str: HTML table string
        """
        thead = ''.join(f'<th>{html.escape(h)}</th>' for h in headers)
        body_rows = []
        for r in rows:
            tds = ''.join(f'<td class="nowrap">{html.escape(str(c))}</td>' for c in r)
            body_rows.append(f'<tr>{tds}</tr>')
        return f'<table class="table"><thead><tr>{thead}</tr></thead><tbody>' + ''.join(body_rows) + '</tbody></table>'

    sections_html = []
    for stitle, ssub, headers, rows in sections:
        sections_html.append(f'''
            <section>
              <header>
                <div>
                  <h2>{html.escape(stitle)}</h2>
                  <p class="sub">{html.escape(ssub)}</p>
                </div>
              </header>
              <div class="wrap">
                {table_html(headers, rows) if rows else '<p class="small">No data matched this section with current thresholds.</p>'}
              </div>
            </section>
        ''')

    params_kv = ' · '.join([f'<span class="badge">{html.escape(k)}: {html.escape(str(v))}</span>' for k,v in params.items()])
    return f'''
    <!doctype html>
    <html lang="en">
      <head>
        <meta charset="utf-8"/>
        <meta name="viewport" content="width=device-width, initial-scale=1"/>
        <title>{html.escape(title)}</title>
        <style>{css}</style>
      </head>
      <body>
        <header>
          <div class="wrap">
            <h1>{html.escape(title)}</h1>
            <div class="meta">{params_kv}</div>
          </div>
        </header>
        <div class="wrap">
          {''.join(sections_html)}
        </div>
        <footer>Generated {html.escape(datetime.now().isoformat(timespec="seconds"))}</footer>
        <script>{js}</script>
      </body>
    </html>
    '''
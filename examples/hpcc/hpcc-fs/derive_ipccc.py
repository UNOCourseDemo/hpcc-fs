#!/usr/bin/env python3
"""Derive paper-ipccc.tex (IEEEtran) from paper.tex (acmart). Keeps the existing
IEEE preamble/title block of paper-ipccc.tex; replaces abstract+body.
IEEE-specific transforms: strip \Description; topos figure -> single-column
fat-tree panel; topo-parking at 0.82\textwidth figure*; IEEEtran bib style."""
import re
src=open("paper.tex").read()
abstract=re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}",src,re.S).group(1).strip()
body=re.search(r"\\maketitle(.*)\\end\{document\}",src,re.S).group(1)
def sd(t):
    out,i=[],0
    while True:
        j=t.find(r"\Description",i)
        if j<0: out.append(t[i:]);break
        out.append(t[i:j]);k=j+len(r"\Description")
        if t[k]=="[":k=t.find("]",k)+1
        d,k2=0,k
        while True:
            if t[k2]=="{":d+=1
            elif t[k2]=="}":
                d-=1
                if d==0:break
            k2+=1
        i=k2+1
    return "".join(out)
body=sd(body)
old=re.search(r"\\begin\{figure\*\}\[t\]\s*\\centering\s*\\begin\{subfigure\}.*?\\label\{fig:topos\}\s*\\end\{figure\*\}",body,re.S)
assert old, "topos block"
new=r"""\begin{figure}[t]
\centering
\includegraphics[width=\columnwidth]{fig_topo_fattree.png}
\caption{The $k=4$ ECMP fat-tree (4 cores, 8 aggs, 8 edges, 16 hosts in 4 pods); the highlighted
line is a representative inter-pod 5-switch path. The tree-fabric topology (unique shortest
paths, no ECMP) is described in the text.\label{fig:topo-ft}}
\label{fig:topos}
\end{figure}"""
body=body.replace(old.group(0),new)
body=body.replace(r"Figure~\ref{fig:topo-tree}", r"Figure~\ref{fig:topos}")
body=body.replace("""\\begin{figure*}[t]
\\centering
\\includegraphics[width=0.92\\textwidth]{fig_topo_parking.png}""",
"""\\begin{figure*}[t]
\\centering
\\includegraphics[width=0.82\\textwidth]{fig_topo_parking.png}""")
body=body.replace(r"\bibliographystyle{ACM-Reference-Format}",r"\bibliographystyle{IEEEtran}")
pre=open("paper-ipccc.tex").read(); pre=pre[:pre.index(r"\begin{abstract}")]
pre=pre.replace(r"\newcommand{\hpccfs}{\textsc{HPCC-FS}\xspace}", r"\newcommand{\hpccfs}{\textsc{RDMA-RCP}\xspace}")
open("paper-ipccc.tex","w").write(pre+"\\begin{abstract}\n"+abstract+"\n\\end{abstract}\n\n\\begin{IEEEkeywords}\ndatacenter networks, congestion control, RDMA, in-network telemetry, max-min fairness, RCP\n\\end{IEEEkeywords}\n"+body+"\n\\end{document}\n")
print("derived")

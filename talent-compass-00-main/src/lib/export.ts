import jsPDF from "jspdf";
import autoTable from "jspdf-autotable";

import type { Candidate, JobDescription, ScoreBreakdown } from "@/lib/scoring/types";
import { scoreCandidate, quadrantOf, recommendationLabel } from "@/lib/scoring/engine";

export interface JobExportRow {
  candidate: Candidate;
  score: ScoreBreakdown;
  quadrant: "safe" | "gem" | "stretch" | "pass";
}

export function buildJobReport(jd: JobDescription, candidates: Candidate[]): JobExportRow[] {
  return candidates
    .map((c) => {
      const s = scoreCandidate(c, jd);
      return { candidate: c, score: s, quadrant: quadrantOf(s) };
    })
    .sort((a, b) => b.score.futureFit - a.score.futureFit);
}

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export function exportJobJson(jd: JobDescription, candidates: Candidate[]) {
  const rows = buildJobReport(jd, candidates);
  const payload = {
    generatedAt: new Date().toISOString(),
    job: jd,
    summary: {
      total: rows.length,
      safeHires: rows.filter((r) => r.quadrant === "safe").length,
      hiddenGems: rows.filter((r) => r.quadrant === "gem").length,
      stretch: rows.filter((r) => r.quadrant === "stretch").length,
      pass: rows.filter((r) => r.quadrant === "pass").length,
      avgFutureFit:
        rows.length > 0
          ? Math.round(rows.reduce((a, r) => a + r.score.futureFit, 0) / rows.length)
          : 0,
    },
    candidates: rows.map((r) => ({
      id: r.candidate.id,
      name: r.candidate.name,
      headline: r.candidate.headline,
      yearsOfExperience: r.candidate.yearsOfExperience,
      atsScore: r.candidate.atsScore,
      quadrant: r.quadrant,
      recommendation: r.score.recommendation,
      currentFit: r.score.currentFit,
      futureFit: r.score.futureFit,
      hiddenGem: r.score.hiddenGem,
      riskScore: r.score.riskScore,
      onboardingWeeks: r.score.onboardingWeeks,
      matchedRequired: r.score.matchedRequired,
      missingRequired: r.score.missingRequired,
      adjacentBridges: r.score.adjacentBridges,
      whyAtsMissed: r.score.whyAtsMissed,
    })),
  };
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
  downloadBlob(blob, `talentdna-${slug(jd.title)}-${stamp()}.json`);
}

export function exportJobPdf(jd: JobDescription, candidates: Candidate[]) {
  const rows = buildJobReport(jd, candidates);
  const doc = new jsPDF({ unit: "pt", format: "a4" });
  const pageW = doc.internal.pageSize.getWidth();

  // Header band
  doc.setFillColor(15, 23, 42);
  doc.rect(0, 0, pageW, 70, "F");
  doc.setTextColor(255, 255, 255);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(18);
  doc.text("TalentDNA · Matching Report", 40, 30);
  doc.setFont("helvetica", "normal");
  doc.setFontSize(10);
  doc.text(`${jd.title} — ${jd.company} · ${jd.location}`, 40, 48);
  doc.setTextColor(148, 163, 184);
  doc.text(`Generated ${new Date().toLocaleString()}`, 40, 62);

  // Summary
  doc.setTextColor(15, 23, 42);
  doc.setFontSize(11);
  doc.setFont("helvetica", "bold");
  doc.text("Summary", 40, 100);
  doc.setFont("helvetica", "normal");
  doc.setFontSize(10);
  const safe = rows.filter((r) => r.quadrant === "safe").length;
  const gem = rows.filter((r) => r.quadrant === "gem").length;
  const stretch = rows.filter((r) => r.quadrant === "stretch").length;
  const pass = rows.filter((r) => r.quadrant === "pass").length;
  const avg =
    rows.length > 0
      ? Math.round(rows.reduce((a, r) => a + r.score.futureFit, 0) / rows.length)
      : 0;
  doc.text(
    `${rows.length} candidates · ${safe} safe hires · ${gem} hidden gems · ${stretch} stretch · ${pass} pass · avg Future Fit ${avg}`,
    40,
    116,
  );

  doc.setFont("helvetica", "bold");
  doc.text("Required skills:", 40, 138);
  doc.setFont("helvetica", "normal");
  doc.text(jd.requiredSkills.join(", ") || "—", 130, 138, { maxWidth: pageW - 170 });
  doc.setFont("helvetica", "bold");
  doc.text("Preferred:", 40, 154);
  doc.setFont("helvetica", "normal");
  doc.text(jd.preferredSkills.join(", ") || "—", 130, 154, { maxWidth: pageW - 170 });

  autoTable(doc, {
    startY: 180,
    head: [["#", "Candidate", "Quadrant", "Rec.", "Current", "Future", "Risk", "Onboard", "ATS"]],
    body: rows.map((r, i) => [
      i + 1,
      `${r.candidate.name}\n${r.candidate.headline}`,
      r.quadrant.toUpperCase(),
      recommendationLabel(r.score.recommendation),
      r.score.currentFit,
      r.score.futureFit,
      r.score.riskScore,
      `${r.score.onboardingWeeks}w`,
      `${r.candidate.atsScore} → ${r.score.futureFit}`,
    ]),
    styles: { fontSize: 9, cellPadding: 5 },
    headStyles: { fillColor: [99, 102, 241], textColor: 255 },
    alternateRowStyles: { fillColor: [248, 250, 252] },
    columnStyles: {
      0: { cellWidth: 24 },
      1: { cellWidth: 150 },
      2: { cellWidth: 56 },
      3: { cellWidth: 56 },
    },
  });

  // Top 5 narrative
  const top = rows.slice(0, 5);
  if (top.length > 0) {
    const afterTable = (doc as unknown as { lastAutoTable?: { finalY: number } }).lastAutoTable?.finalY ?? 200;
    let y = afterTable + 24;
    doc.setFont("helvetica", "bold");
    doc.setFontSize(11);
    doc.text("Top 5 — why TalentDNA flagged them", 40, y);
    y += 14;
    doc.setFont("helvetica", "normal");
    doc.setFontSize(9);
    for (const r of top) {
      if (y > 760) {
        doc.addPage();
        y = 60;
      }
      doc.setFont("helvetica", "bold");
      doc.text(`${r.candidate.name} — ${recommendationLabel(r.score.recommendation)}`, 40, y);
      y += 12;
      doc.setFont("helvetica", "normal");
      const lines = doc.splitTextToSize(r.score.whyAtsMissed.join(" "), pageW - 80);
      doc.text(lines, 40, y);
      y += lines.length * 11 + 10;
    }
  }

  doc.save(`talentdna-${slug(jd.title)}-${stamp()}.pdf`);
}

function slug(s: string) {
  return s.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");
}
function stamp() {
  const d = new Date();
  return `${d.getFullYear()}${String(d.getMonth() + 1).padStart(2, "0")}${String(d.getDate()).padStart(2, "0")}`;
}

import { useCallback, useRef, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { apiRequest } from "@/lib/queryClient";
import { useResume } from "@/lib/resume-context";
import { Link } from "wouter";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Skeleton } from "@/components/ui/skeleton";
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
  Legend,
} from "recharts";
import {
  FileSearch,
  FileUp,
  FileImage,
  Briefcase,
  GraduationCap,
  Sparkles,
  ArrowRight,
  Loader2,
  X,
  FolderKanban,
  Code2,
} from "lucide-react";

const CHART_COLORS = [
  "hsl(225, 73%, 57%)",
  "hsl(262, 83%, 58%)",
  "hsl(142, 71%, 45%)",
  "hsl(38, 92%, 50%)",
  "hsl(0, 84%, 60%)",
  "hsl(195, 74%, 50%)",
  "hsl(325, 65%, 55%)",
  "hsl(170, 60%, 42%)",
];

const SAMPLE_RESUME = `Senior Software Engineer with 6+ years of experience in Python, Java, and cloud-based architectures. Proficient in machine learning, data analysis, SQL, and building scalable distributed systems. Strong background in React, Node.js, Docker, Kubernetes, and CI/CD pipelines. Master's degree in Computer Science from ASU. Experience with AWS, TensorFlow, NLP, and Agile development methodologies. Led teams of 5-8 engineers, conducted code reviews, and mentored junior developers. Published research in AAAI on deep learning for NLP.`;

export default function Analyze() {
  const { resumeText, setResumeText, parsedResume, setParsedResume } =
    useResume();
  const [localText, setLocalText] = useState(resumeText);
  const [pdfFile, setPdfFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const parseMutation = useMutation({
    mutationFn: async (text: string) => {
      const res = await apiRequest("POST", "/api/parse-resume", {
        text,
      });
      return res.json();
    },
    onSuccess: (data) => {
      setParsedResume(data);
      setResumeText(localText);
    },
  });

  const pdfMutation = useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData();
      formData.append("file", file);
      // Use the same API_BASE logic as apiRequest so deployed URLs work
      const base = "__PORT_5000__".startsWith("__") ? "" : "__PORT_5000__";
      const res = await fetch(`${base}/api/parse-resume-pdf`, {
        method: "POST",
        body: formData,
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Upload failed" }));
        throw new Error(err.detail || "Upload failed");
      }
      return res.json();
    },
    onSuccess: (data) => {
      setParsedResume(data);
      if (data.extracted_text) {
        setLocalText(data.extracted_text);
        setResumeText(data.extracted_text);
      }
    },
  });

  const handleAnalyze = () => {
    if (pdfFile) {
      pdfMutation.mutate(pdfFile);
      return;
    }
    if (!localText.trim()) return;
    parseMutation.mutate(localText);
  };

  const ACCEPTED_TYPES = new Set([
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
    "image/jpeg",
    "image/png",
    "image/bmp",
    "image/tiff",
    "image/webp",
  ]);
  const ACCEPTED_EXTS = /\.(pdf|docx|jpe?g|png|bmp|tiff?|webp)$/i;

  const handleFileSelect = useCallback((file: File) => {
    if (ACCEPTED_TYPES.has(file.type) || ACCEPTED_EXTS.test(file.name)) {
      setPdfFile(file);
      setLocalText("");
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFileSelect(file);
  }, [handleFileSelect]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const clearPdf = () => {
    setPdfFile(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const isLoading = parseMutation.isPending || pdfMutation.isPending;
  const isError = parseMutation.isError || pdfMutation.isError;
  const errorMessage = pdfMutation.isError
    ? (pdfMutation.error as Error)?.message || "Failed to parse PDF."
    : "Failed to analyze resume. Is the backend running on port 8000?";

  // skill_categories is { skill: category } — group by category name for pie chart
  const categoryData = parsedResume?.skill_categories
    ? (() => {
        const grouped: Record<string, number> = {};
        Object.values(parsedResume.skill_categories!).forEach((cat) => {
          grouped[cat as string] = (grouped[cat as string] || 0) + 1;
        });
        return Object.entries(grouped).map(([name, value]) => ({ name, value }));
      })()
    : parsedResume?.skill_scores
      ? (() => {
          // Group by score ranges if no categories
          const scores = Object.values(parsedResume.skill_scores!);
          const high = scores.filter((v) => v >= 0.8).length;
          const mid = scores.filter((v) => v >= 0.5 && v < 0.8).length;
          const low = scores.filter((v) => v < 0.5).length;
          return [
            { name: "Expert (≥0.8)", value: high },
            { name: "Proficient (0.5–0.8)", value: mid },
            { name: "Familiar (<0.5)", value: low },
          ].filter((d) => d.value > 0);
        })()
      : [];

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      <div>
        <h1 className="text-lg font-bold tracking-tight" data-testid="text-page-title">
          Resume Analyzer
        </h1>
        <p className="text-xs text-muted-foreground mt-1">
          Upload a resume (PDF or image) or paste text to extract skills,
          experience, and education using NLP.
        </p>
      </div>

      {/* Input section */}
      <Card className="border-border">
        <CardContent className="p-5 space-y-4">
          {/* PDF upload drop zone */}
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.docx,.jpg,.jpeg,.png,.bmp,.tiff,.tif,.webp"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) handleFileSelect(file);
            }}
            data-testid="input-pdf-file"
          />

          {pdfFile ? (
            <div className="flex items-center gap-3 rounded-lg border border-border bg-muted/40 px-4 py-3">
              <FileUp className="w-5 h-5 text-primary shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate" data-testid="text-pdf-name">
                  {pdfFile.name}
                </p>
                <p className="text-xs text-muted-foreground">
                  {(pdfFile.size / 1024).toFixed(1)} KB — ready to analyze
                </p>
              </div>
              <Button
                variant="ghost"
                size="sm"
                className="h-7 w-7 p-0 shrink-0"
                onClick={clearPdf}
                data-testid="button-clear-pdf"
              >
                <X className="w-3.5 h-3.5" />
              </Button>
            </div>
          ) : (
            <div
              className={`relative rounded-lg border-2 border-dashed transition-colors cursor-pointer ${
                isDragging
                  ? "border-primary bg-primary/5"
                  : "border-border hover:border-muted-foreground/40"
              }`}
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onClick={() => fileInputRef.current?.click()}
              data-testid="dropzone-pdf"
            >
              <div className="flex flex-col items-center justify-center py-5 gap-1.5 pointer-events-none">
                <div className="flex items-center gap-2">
                  <FileUp className="w-5 h-5 text-muted-foreground" />
                  <FileImage className="w-5 h-5 text-muted-foreground" />
                </div>
                <p className="text-xs text-muted-foreground">
                  Drop a PDF, DOCX, or image here, or{" "}
                  <span className="text-primary font-medium">browse</span>
                </p>
                <p className="text-[10px] text-muted-foreground/60">
                  PDF, DOCX, JPG, PNG, BMP, TIFF, WebP
                </p>
              </div>
            </div>
          )}

          {/* Divider */}
          <div className="flex items-center gap-3">
            <div className="flex-1 border-t border-border" />
            <span className="text-[10px] uppercase tracking-widest text-muted-foreground">
              or paste text
            </span>
            <div className="flex-1 border-t border-border" />
          </div>

          <Textarea
            placeholder="Paste your resume text here..."
            className="min-h-[140px] text-sm leading-relaxed resize-y bg-background"
            value={localText}
            onChange={(e) => {
              setLocalText(e.target.value);
              if (e.target.value.trim()) clearPdf();
            }}
            data-testid="input-resume-text"
          />
          <div className="flex items-center gap-3">
            <Button
              onClick={handleAnalyze}
              disabled={(!localText.trim() && !pdfFile) || isLoading}
              size="sm"
              data-testid="button-analyze"
            >
              {isLoading ? (
                <Loader2 className="w-3.5 h-3.5 mr-1.5 animate-spin" />
              ) : (
                <FileSearch className="w-3.5 h-3.5 mr-1.5" />
              )}
              {pdfFile
                ? (pdfFile.name.toLowerCase().endsWith(".pdf") || pdfFile.name.toLowerCase().endsWith(".docx"))
                  ? pdfFile.name.toLowerCase().endsWith(".docx") ? "Analyze DOCX" : "Analyze PDF"
                  : "Analyze Image"
                : "Analyze Resume"}
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setLocalText(SAMPLE_RESUME);
                clearPdf();
              }}
              data-testid="button-sample"
            >
              <Sparkles className="w-3.5 h-3.5 mr-1.5" />
              Load Sample
            </Button>
          </div>
          {isError && (
            <p className="text-xs text-destructive" data-testid="text-error">
              {errorMessage}
            </p>
          )}
        </CardContent>
      </Card>

      {/* Loading state */}
      {isLoading && (
        <div className="grid md:grid-cols-2 gap-4">
          <Card className="border-border">
            <CardContent className="p-5">
              <Skeleton className="h-4 w-32 mb-4" />
              <div className="space-y-2">
                {[1, 2, 3, 4].map((i) => (
                  <Skeleton key={i} className="h-6 w-full" />
                ))}
              </div>
            </CardContent>
          </Card>
          <Card className="border-border">
            <CardContent className="p-5">
              <Skeleton className="h-48 w-full rounded-lg" />
            </CardContent>
          </Card>
        </div>
      )}

      {/* Results */}
      {parsedResume && !isLoading && (
        <div className="space-y-4">
          {/* Meta cards */}
          <div className="grid grid-cols-2 gap-4">
            <Card className="border-border">
              <CardContent className="p-4 flex items-center gap-3">
                <div className="w-9 h-9 rounded-lg bg-chart-4/10 flex items-center justify-center">
                  <Briefcase className="w-4 h-4 text-chart-4" />
                </div>
                <div>
                  <p
                    className="text-lg font-semibold tabular-nums"
                    data-testid="text-experience"
                  >
                    {(parsedResume.years_experience ?? parsedResume.experience_years) != null
                      ? `${parsedResume.years_experience ?? parsedResume.experience_years} yrs`
                      : "N/A"}
                  </p>
                  <p className="text-xs text-muted-foreground">Experience</p>
                </div>
              </CardContent>
            </Card>
            <Card className="border-border">
              <CardContent className="p-4 flex items-center gap-3">
                <div className="w-9 h-9 rounded-lg bg-chart-2/10 flex items-center justify-center">
                  <GraduationCap className="w-4 h-4 text-chart-2" />
                </div>
                <div>
                  <p
                    className="text-sm font-semibold"
                    data-testid="text-education"
                  >
                    {parsedResume.education_level}
                  </p>
                  <p className="text-xs text-muted-foreground">Education</p>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Skills + chart */}
          <div className="grid md:grid-cols-2 gap-4">
            <Card className="border-border">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-semibold">
                  Extracted Skills ({parsedResume.skills?.length ?? Object.keys(parsedResume.skill_scores ?? {}).length})
                </CardTitle>
              </CardHeader>
              <CardContent className="pb-5">
                <div
                  className="flex flex-wrap gap-1.5 max-h-[300px] overflow-y-auto"
                  data-testid="container-skills"
                >
                  {(parsedResume.skills || []).map((skill) => {
                      const s = parsedResume.skill_scores?.[skill] ?? 0;
                      const colorClass =
                        s >= 0.8
                          ? "bg-chart-1/15 text-chart-1 border-chart-1/20"
                          : s >= 0.5
                            ? "bg-chart-3/15 text-chart-3 border-chart-3/20"
                            : "bg-muted text-muted-foreground border-border";
                      return (
                        <Badge
                          key={skill}
                          variant="outline"
                          className={`text-[11px] font-medium ${colorClass}`}
                          data-testid={`badge-skill-${skill}`}
                        >
                          {skill}
                          {s > 0 && (
                            <span className="ml-1 opacity-60 tabular-nums">
                              {(s * 100).toFixed(0)}
                            </span>
                          )}
                        </Badge>
                      );
                    })}
                </div>
              </CardContent>
            </Card>

            <Card className="border-border">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-semibold">
                  Skill Breakdown
                </CardTitle>
              </CardHeader>
              <CardContent>
                {categoryData.length > 0 ? (
                  <ResponsiveContainer width="100%" height={260}>
                    <PieChart>
                      <Pie
                        data={categoryData}
                        cx="50%"
                        cy="50%"
                        innerRadius={55}
                        outerRadius={90}
                        paddingAngle={3}
                        dataKey="value"
                        stroke="none"
                      >
                        {categoryData.map((_entry, idx) => (
                          <Cell
                            key={idx}
                            fill={CHART_COLORS[idx % CHART_COLORS.length]}
                          />
                        ))}
                      </Pie>
                      <Tooltip
                        contentStyle={{
                          background: "hsl(222, 40%, 9%)",
                          border: "1px solid hsl(222, 30%, 14%)",
                          borderRadius: "8px",
                          fontSize: "12px",
                          color: "hsl(210, 20%, 90%)",
                        }}
                      />
                      <Legend
                        wrapperStyle={{ fontSize: "11px" }}
                        iconSize={8}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-[260px] flex items-center justify-center text-xs text-muted-foreground">
                    No category data available
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Projects section */}
          {parsedResume.projects && parsedResume.projects.length > 0 && (
            <Card className="border-border">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-semibold flex items-center gap-2">
                  <FolderKanban className="w-4 h-4 text-chart-2" />
                  Projects ({parsedResume.projects.length})
                </CardTitle>
              </CardHeader>
              <CardContent className="pb-5 space-y-3">
                {parsedResume.projects.map((proj: { name: string; tech_stack: string[]; description: string }, idx: number) => (
                  <div
                    key={idx}
                    className="rounded-lg border border-border bg-muted/30 p-3 space-y-1.5"
                    data-testid={`project-card-${idx}`}
                  >
                    <p className="text-sm font-semibold leading-tight" data-testid={`project-name-${idx}`}>
                      {proj.name}
                    </p>
                    {proj.description && (
                      <p className="text-xs text-muted-foreground leading-relaxed" data-testid={`project-desc-${idx}`}>
                        {proj.description}
                      </p>
                    )}
                    {proj.tech_stack.length > 0 && (
                      <div className="flex items-center gap-1.5 flex-wrap pt-0.5">
                        <Code2 className="w-3 h-3 text-muted-foreground shrink-0" />
                        {proj.tech_stack.map((tech) => (
                          <Badge
                            key={tech}
                            variant="outline"
                            className="text-[10px] font-medium bg-chart-2/10 text-chart-2 border-chart-2/20 py-0"
                            data-testid={`project-tech-${idx}-${tech}`}
                          >
                            {tech}
                          </Badge>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </CardContent>
            </Card>
          )}

          {/* CTA to next step */}
          <Card className="border-border bg-primary/5">
            <CardContent className="p-4 flex items-center justify-between">
              <p className="text-xs text-muted-foreground">
                Skills extracted — continue to find matching roles.
              </p>
              <Link href="/match">
                <Button size="sm" variant="outline" data-testid="button-go-match">
                  Match Roles <ArrowRight className="w-3.5 h-3.5 ml-1.5" />
                </Button>
              </Link>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}

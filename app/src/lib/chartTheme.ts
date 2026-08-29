/** Palette Asclepios pour Chart.js (hex = rendu canvas fiable) */
export const chartColors = {
  primary: '#1A7A60',
  primarySoft: 'rgba(26, 122, 96, 0.15)',
  primaryFill: 'rgba(26, 122, 96, 0.12)',
  mint: '#7BC5B4',
  accent: '#F3A72E',
  marker: '#3B82F6',
  markerSoft: 'rgba(59, 130, 246, 0.15)',
  dose: '#1A7A60',
  danger: '#DC2626',
  muted: '#7D8B96',
  border: '#D4E0DC',
  grid: 'rgba(26, 122, 96, 0.08)',
  text: '#1A3D38',
  card: '#FFFFFF',
} as const

export function baseChartOptions() {
  return {
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
      mode: 'index' as const,
      intersect: false,
    },
    plugins: {
      legend: {
        position: 'top' as const,
        align: 'end' as const,
        labels: {
          boxWidth: 10,
          boxHeight: 10,
          usePointStyle: true,
          pointStyle: 'circle' as const,
          color: chartColors.muted,
          font: { size: 12, family: "'Inter', system-ui, sans-serif" },
          padding: 16,
        },
      },
      tooltip: {
        backgroundColor: chartColors.card,
        titleColor: chartColors.text,
        bodyColor: chartColors.muted,
        borderColor: chartColors.border,
        borderWidth: 1,
        padding: 10,
        cornerRadius: 8,
        displayColors: true,
        titleFont: { size: 12, weight: 'bold' as const },
        bodyFont: { size: 12 },
      },
    },
    scales: {
      x: {
        type: 'time' as const,
        grid: { color: chartColors.grid, drawBorder: false },
        ticks: {
          color: chartColors.muted,
          font: { size: 11 },
          maxRotation: 0,
        },
        border: { display: false },
      },
      y: {
        grid: { color: chartColors.grid, drawBorder: false },
        ticks: {
          color: chartColors.muted,
          font: { size: 11 },
        },
        border: { display: false },
      },
    },
  }
}

export function parseFrDate(d: string): Date | null {
  const m = d.match(/^(\d{2})\/(\d{2})\/(\d{4})$/)
  if (!m) return null
  return new Date(Number(m[3]), Number(m[2]) - 1, Number(m[1]))
}

export function formatFrDate(d: Date): string {
  return d.toLocaleDateString('fr-FR', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  })
}

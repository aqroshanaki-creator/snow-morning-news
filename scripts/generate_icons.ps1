Add-Type -AssemblyName System.Drawing

function Create-AppIcon {
    param(
        [int]$size,
        [string]$outPath
    )
    $bmp = New-Object System.Drawing.Bitmap($size, $size)
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
    $g.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAlias

    $rect = New-Object System.Drawing.Rectangle(0, 0, $size, $size)
    $brush = New-Object System.Drawing.Drawing2D.LinearGradientBrush(
        $rect,
        [System.Drawing.Color]::FromArgb(255, 255, 126, 179),
        [System.Drawing.Color]::FromArgb(255, 224, 64, 123),
        [System.Drawing.Drawing2D.LinearGradientMode]::ForwardDiagonal
    )
    $g.FillRectangle($brush, $rect)

    $pen = New-Object System.Drawing.Pen([System.Drawing.Color]::White, ($size / 16))
    $pen.StartCap = [System.Drawing.Drawing2D.LineCap]::Round
    $pen.EndCap = [System.Drawing.Drawing2D.LineCap]::Round

    $center = [float]($size / 2)
    $arm = [float]($size * 0.3)

    $g.DrawLine($pen, $center, ($center - $arm), $center, ($center + $arm))
    $g.DrawLine($pen, ($center - $arm), $center, ($center + $arm), $center)

    $dotBrush = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::White)
    $dotRadius = [float]($size * 0.12)
    $g.FillEllipse($dotBrush, ($center - $dotRadius), ($center - $dotRadius), ($dotRadius * 2), ($dotRadius * 2))

    $innerBrush = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(255, 224, 64, 123))
    $innerRadius = [float]($size * 0.07)
    $g.FillEllipse($innerBrush, ($center - $innerRadius), ($center - $innerRadius), ($innerRadius * 2), ($innerRadius * 2))

    $g.Dispose()
    $bmp.Save($outPath, [System.Drawing.Imaging.ImageFormat]::Png)
    $bmp.Dispose()
}

$iconsDir = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\web\icons"
Create-AppIcon 192 (Join-Path $iconsDir "icon-192.png")
Create-AppIcon 512 (Join-Path $iconsDir "icon-512.png")
Write-Host "PNG icons created successfully!"


# GitHub Actions 触发脚本
# 用于触发 TikTokDownloader 的 run-script workflow

param(
    [string]$Cookie = "test_cookie",
    [string]$Action = "comment",
    [string]$Kwargs = '{"urls": "https://www.douyin.com/user/self?from_tab_name=main&modal_id=7253355171290352955&showTab=favorite_collection", "storage_format": "csv", "max_pages": 3}'
)

# GitHub 配置
$GitHubRepo = "wth461694678/TikTokDownloader"
$GitHubToken = "test_token"
$WorkflowFile = "run-script.yml"
$Branch = "master"

# API 端点
$ApiUrl = "https://api.github.com/repos/$GitHubRepo/actions/workflows/$WorkflowFile/dispatches"

Write-Host "===========================================" -ForegroundColor Cyan
Write-Host "GitHub Actions 触发脚本" -ForegroundColor Cyan
Write-Host "===========================================" -ForegroundColor Cyan
Write-Host "仓库: $GitHubRepo" -ForegroundColor Green
Write-Host "工作流: $WorkflowFile" -ForegroundColor Green
Write-Host "分支: $Branch" -ForegroundColor Green
Write-Host "操作: $Action" -ForegroundColor Green
Write-Host "参数: $Kwargs" -ForegroundColor Green
Write-Host "===========================================" -ForegroundColor Cyan

# 构建请求体
$RequestBody = @{
    ref = $Branch
    inputs = @{
        cookie = $Cookie
        action = $Action
        kwargs = $Kwargs
    }
} | ConvertTo-Json -Depth 3

Write-Host "发送请求到 GitHub API..." -ForegroundColor Yellow
Write-Host "URL: $ApiUrl" -ForegroundColor Gray
Write-Host "请求体:" -ForegroundColor Gray
Write-Host $RequestBody -ForegroundColor Gray
Write-Host "Kwargs 原始值: $Kwargs" -ForegroundColor Gray

# 构建请求头
$Headers = @{
    "Accept" = "application/vnd.github.v3+json"
    "Authorization" = "token $GitHubToken"
    "User-Agent" = "PowerShell-Script"
}

try {
    # 发送 POST 请求触发 workflow
    $Response = Invoke-RestMethod -Uri $ApiUrl -Method POST -Headers $Headers -Body $RequestBody -ContentType "application/json"
    
    Write-Host "✅ GitHub Actions 触发成功!" -ForegroundColor Green
    Write-Host "响应: $Response" -ForegroundColor Green
    
    # 显示 GitHub Actions 页面链接
    $ActionsUrl = "https://github.com/$GitHubRepo/actions"
    Write-Host "🔗 查看执行状态: $ActionsUrl" -ForegroundColor Blue
    
    # 等待几秒钟，然后检查最新的 workflow 运行状态
    Write-Host "等待 5 秒后检查运行状态..." -ForegroundColor Yellow
    Start-Sleep -Seconds 5
    
    # 获取最新的 workflow 运行状态
    $RunsUrl = "https://api.github.com/repos/$GitHubRepo/actions/workflows/$WorkflowFile/runs?per_page=1"
    try {
        $RunsResponse = Invoke-RestMethod -Uri $RunsUrl -Method GET -Headers $Headers
        if ($RunsResponse.workflow_runs -and $RunsResponse.workflow_runs.Count -gt 0) {
            $LatestRun = $RunsResponse.workflow_runs[0]
            Write-Host "📊 最新运行状态:" -ForegroundColor Cyan
            Write-Host "  - 运行ID: $($LatestRun.id)" -ForegroundColor White
            Write-Host "  - 状态: $($LatestRun.status)" -ForegroundColor White
            Write-Host "  - 结论: $($LatestRun.conclusion)" -ForegroundColor White
            Write-Host "  - 创建时间: $($LatestRun.created_at)" -ForegroundColor White
            Write-Host "  - 运行链接: $($LatestRun.html_url)" -ForegroundColor Blue
        }
    }
    catch {
        Write-Host "⚠️ 无法获取运行状态: $($_.Exception.Message)" -ForegroundColor Yellow
    }
    
}
catch {
    Write-Host "❌ 触发失败!" -ForegroundColor Red
    Write-Host "错误信息: $($_.Exception.Message)" -ForegroundColor Red
    
    # 如果有响应内容，显示详细错误
    if ($_.Exception.Response) {
        try {
            $ErrorStream = $_.Exception.Response.GetResponseStream()
            $Reader = New-Object System.IO.StreamReader($ErrorStream)
            $ErrorBody = $Reader.ReadToEnd()
            Write-Host "详细错误: $ErrorBody" -ForegroundColor Red
        }
        catch {
            Write-Host "无法读取错误详情" -ForegroundColor Red
        }
    }
    
    exit 1
}

Write-Host "===========================================" -ForegroundColor Cyan
Write-Host "脚本执行完成" -ForegroundColor Cyan
Write-Host "===========================================" -ForegroundColor Cyan
# Generate traffic so that logs, metrics and traces show up in Grafana.
# Usage: .\scripts\traffic.ps1            (normal traffic)
#        .\scripts\traffic.ps1 -Errors 5  (also 5 requests that return HTTP 500 -> alert)
param(
    [int]$Requests = 30,
    [int]$Errors = 0,
    [string]$BaseUrl = "http://localhost:8000"
)

$json = @{ "Content-Type" = "application/json" }

foreach ($name in "101", "102", "201") {
    try {
        Invoke-RestMethod "$BaseUrl/rooms" -Method Post -Headers $json `
            -Body (@{ name = $name; capacity = 2 } | ConvertTo-Json) | Out-Null
    } catch { }  # room already exists (409) - fine
}
$rooms = Invoke-RestMethod "$BaseUrl/rooms"

$ok = 0; $conflicts = 0
for ($i = 0; $i -lt $Requests; $i++) {
    $room = $rooms | Get-Random
    $start = (Get-Date).Date.AddDays((Get-Random -Minimum 1 -Maximum 60))
    $body = @{
        room_id    = $room.id
        guest_name = "Guest $i"
        check_in   = $start.ToString("yyyy-MM-dd")
        check_out  = $start.AddDays((Get-Random -Minimum 1 -Maximum 5)).ToString("yyyy-MM-dd")
    } | ConvertTo-Json
    try {
        Invoke-RestMethod "$BaseUrl/bookings" -Method Post -Headers $json -Body $body | Out-Null
        $ok++
    } catch { $conflicts++ }
    Invoke-RestMethod "$BaseUrl/bookings?room_id=$($room.id)" | Out-Null
}

for ($i = 0; $i -lt $Errors; $i++) {
    try { Invoke-RestMethod "$BaseUrl/debug/error" | Out-Null } catch { }
}

Write-Host "Bookings created: $ok, conflicts (409): $conflicts, errors (500): $Errors"

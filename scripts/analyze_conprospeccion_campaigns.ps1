param(
    [string]$Root = (Resolve-Path ".").Path
)

$ErrorActionPreference = "Stop"

$apolloPath = Join-Path $Root "CLIENTES\GBS_LOGISTICS\08_BASES_Y_CALIFICACION\00_fuentes\apollo\normalizado\apollo_cp_enriquecida_20260530_113354.csv"
$snovPath = Join-Path $Root "CLIENTES\GBS_LOGISTICS\08_BASES_Y_CALIFICACION\00_fuentes\snov\normalizado\snov_cp_enriquecida_20260530_113354.csv"
$outDir = Join-Path $Root "data\outputs\Conprospeccion_Campanas"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

function Clean([object]$v) {
    if ($null -eq $v) { return "" }
    $s = ([string]$v).Trim()
    if ($s -match '^(nan|none|null|n/a|-)$') { return "" }
    return $s
}

function Has-Email([string]$email) {
    return ($email -match '^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$')
}

function Get-Domain([string]$email, [string]$website) {
    if (Has-Email $email) {
        $d = ($email.Split("@")[-1]).ToLower()
        if ($d -notmatch '^(gmail|hotmail|yahoo|outlook|icloud|live|msn|aol|protonmail)\.') { return $d }
    }
    $w = (Clean $website).ToLower()
    $w = $w -replace '^https?://','' -replace '^www\.',''
    if ($w) { return ($w.Split("/")[0]) }
    return ""
}

function Norm-Company([string]$company) {
    $s = (Clean $company).ToLower()
    $s = $s -replace '[^\p{L}\p{Nd} ]',' '
    $s = $s -replace '\b(s\.?a\.?|spa|sac|srl|ltda|limitada|inc|corp|company|co|llc|gmbh|sas)\b',''
    $s = $s -replace '\s+',' '
    return $s.Trim()
}

function Norm-Size([string]$size) {
    $s = Clean $size
    if (-not $s) { return "Desconocido" }
    $nums = [regex]::Matches($s, '\d+') | ForEach-Object { [int]$_.Value }
    if ($nums.Count -eq 0) { return $s }
    $n = ($nums | Measure-Object -Maximum).Maximum
    if ($n -le 10) { return "1-10" }
    if ($n -le 50) { return "11-50" }
    if ($n -le 200) { return "51-200" }
    if ($n -le 500) { return "201-500" }
    if ($n -le 1000) { return "501-1000" }
    return "1000+"
}

function Norm-Country([string]$country) {
    $s = (Clean $country).ToLower()
    if ($s -match 'chile') { return "Chile" }
    if ($s -match 'peru|perú') { return "Peru" }
    if ($s -match 'colombia') { return "Colombia" }
    if ($s -match 'argentina') { return "Argentina" }
    if ($s -match 'mexico|méxico') { return "Mexico" }
    if ($s -match 'brazil|brasil') { return "Brasil" }
    if ($s -match 'spain|españa|espana') { return "Espana" }
    if ($s -match 'united states|usa|eeuu') { return "USA" }
    if ($s) { return (Get-Culture).TextInfo.ToTitleCase($s) }
    return "Desconocido"
}

function Segment-Industry([string]$industry, [string]$company) {
    $t = ("$industry $company").ToLower()
    if ($t -match 'software|saas|technology|information technology|internet|cloud|computer|it services|telecom|digital|e-commerce|ecommerce') { return "Tecnologia, SaaS y servicios IT" }
    if ($t -match 'marketing|advertising|publicidad|media|agency|agencia|market research|events services') { return "Marketing, agencias y medios" }
    if ($t -match 'consulting|professional services|management consulting|business consulting|outsourcing|bpo|servicios profesionales') { return "Consultoria y servicios B2B" }
    if ($t -match 'financial|bank|banking|fintech|factoring|insurance|seguros|capital markets|investment|credit|credito|crédito') { return "Finanzas, fintech y seguros" }
    if ($t -match 'staffing|recruiting|human resources|headhunt|talent|rrhh|recursos humanos') { return "RRHH, staffing y reclutamiento" }
    if ($t -match 'logistics|transport|freight|supply chain|warehousing|forwarder|courier|cadena de suministro') { return "Logistica, transporte y supply chain" }
    if ($t -match 'real estate|construction|building|architecture|inmobili|construccion|construcción') { return "Inmobiliaria, construccion e infraestructura" }
    if ($t -match 'retail|consumer goods|wholesale|distribution|distributor|apparel|food|beverage|wine|supermarket|restaurants') { return "Retail, consumo y distribucion" }
    if ($t -match 'industrial|machinery|manufacturing|mining|automotive|medical devices|equipment|engineering') { return "Industrial, manufactura y equipamiento" }
    if ($t -match 'education|higher education|training|capacitacion|capacitación') { return "Educacion y capacitacion" }
    return "Otros sectores"
}

function Segment-Title([string]$title) {
    $t = (Clean $title).ToLower()
    if ($t -match 'ceo|founder|co-founder|owner|socio|gerente general|general manager|managing director|country manager|president') { return "Dueño, founder o gerencia general" }
    if ($t -match 'sales|comercial|commercial|business development|revenue|growth|account executive|ventas|partnership') { return "Comercial, ventas, growth o revenue" }
    if ($t -match 'marketing|demand generation|go-to-market|brand|crm|customer acquisition') { return "Marketing, demanda o CRM" }
    if ($t -match 'operations|operaciones|supply chain|logistics|procurement|compras') { return "Operaciones, compras o supply chain" }
    if ($t -match 'finance|finanzas|administration|administracion|administración|cfo') { return "Finanzas o administracion" }
    if ($t -match 'hr|human resources|people|talent|recruit') { return "RRHH o talento" }
    if ($t -match 'director|manager|head|jefe|gerente|lead') { return "Gerencia funcional" }
    if ($t) { return "Otros cargos" }
    return "Sin cargo"
}

function Industry-Fit([string]$segment) {
    switch ($segment) {
        "Tecnologia, SaaS y servicios IT" { 30; break }
        "Marketing, agencias y medios" { 30; break }
        "Consultoria y servicios B2B" { 28; break }
        "Finanzas, fintech y seguros" { 27; break }
        "RRHH, staffing y reclutamiento" { 26; break }
        "Logistica, transporte y supply chain" { 23; break }
        "Inmobiliaria, construccion e infraestructura" { 20; break }
        "Industrial, manufactura y equipamiento" { 18; break }
        "Retail, consumo y distribucion" { 16; break }
        "Educacion y capacitacion" { 14; break }
        default { 8 }
    }
}

function Title-Fit([string]$segment) {
    switch ($segment) {
        "Comercial, ventas, growth o revenue" { 30; break }
        "Dueño, founder o gerencia general" { 28; break }
        "Marketing, demanda o CRM" { 26; break }
        "RRHH o talento" { 20; break }
        "Gerencia funcional" { 16; break }
        "Finanzas o administracion" { 12; break }
        "Operaciones, compras o supply chain" { 10; break }
        default { 5 }
    }
}

function Country-Fit([string]$country) {
    switch ($country) {
        "Chile" { 12; break }
        "Peru" { 10; break }
        "Colombia" { 9; break }
        "Mexico" { 8; break }
        "Argentina" { 7; break }
        default { 4 }
    }
}

function Size-Fit([string]$size) {
    switch ($size) {
        "11-50" { 12; break }
        "51-200" { 14; break }
        "201-500" { 12; break }
        "501-1000" { 8; break }
        "1000+" { 6; break }
        "1-10" { 5; break }
        default { 6 }
    }
}

Write-Host "Leyendo Apollo..."
$apollo = Import-Csv -LiteralPath $apolloPath | ForEach-Object {
    $email = Clean $_.Email
    $company = Clean $_.'Company Name'
    if (-not $company) { $company = Clean $_.cp_company_name }
    $industry = Clean $_.Industry
    if (-not $industry) { $industry = Clean $_.cp_industry_normalized }
    $country = Clean $_.'Company Country'
    if (-not $country) { $country = Clean $_.Country }
    [pscustomobject]@{
        source = "Apollo"
        company = $company
        company_key = Norm-Company $company
        domain = Get-Domain $email (Clean $_.Website)
        contact = ((Clean $_.'First Name') + " " + (Clean $_.'Last Name')).Trim()
        title = Clean $_.Title
        title_segment = Segment-Title (Clean $_.Title)
        industry = $industry
        industry_segment = Segment-Industry $industry $company
        country = Norm-Country $country
        size = Norm-Size (Clean $_.'# Employees')
        email = $email
        has_email = Has-Email $email
        email_status = Clean $_.'Email Status'
        verified_email = ((Clean $_.'Email Status') -match 'verified|valid')
        website = Clean $_.Website
        linkedin = Clean $_.'Person Linkedin Url'
    }
}

Write-Host "Leyendo Snov..."
$snov = Import-Csv -LiteralPath $snovPath | ForEach-Object {
    $email = Clean $_.Email
    $company = Clean $_.'Nombre de la empresa'
    if (-not $company) { $company = Clean $_.cp_company_name }
    $industry = Clean $_.'Sector de la empresa'
    if (-not $industry) { $industry = Clean $_.Sector }
    if (-not $industry) { $industry = Clean $_.cp_industry_normalized }
    $country = Clean $_.'País de la empresa'
    if (-not $country) { $country = Clean $_.'País' }
    [pscustomobject]@{
        source = "Snov"
        company = $company
        company_key = Norm-Company $company
        domain = Get-Domain $email (Clean $_.'URL de la empresa')
        contact = Clean $_.'Nombre completo'
        title = Clean $_.Cargo
        title_segment = Segment-Title (Clean $_.Cargo)
        industry = $industry
        industry_segment = Segment-Industry $industry $company
        country = Norm-Country $country
        size = Norm-Size (Clean $_.'Tamaño de la empresa')
        email = $email
        has_email = Has-Email $email
        email_status = Clean $_.'Estado del email'
        verified_email = ((Clean $_.'Estado del email') -match 'valid|verified')
        website = Clean $_.'URL de la empresa'
        linkedin = Clean $_.LinkedIn
    }
}

$all = @($apollo) + @($snov)
$withEmail = $all | Where-Object { $_.has_email -and $_.company_key }

foreach ($r in $withEmail) {
    $score = 0
    $score += Industry-Fit $r.industry_segment
    $score += Title-Fit $r.title_segment
    $score += Country-Fit $r.country
    $score += Size-Fit $r.size
    if ($r.verified_email) { $score += 8 } else { $score += 3 }
    if ($r.domain) { $score += 4 }
    $r | Add-Member -NotePropertyName cp_fit_score -NotePropertyValue ([Math]::Min($score,100))
}

$companyGroups = $withEmail | Group-Object { if ($_.domain) { "domain:" + $_.domain } else { "name:" + $_.company_key } }
$companies = foreach ($g in $companyGroups) {
    $rows = @($g.Group)
    $top = $rows | Sort-Object cp_fit_score -Descending | Select-Object -First 1
    $emailCount = ($rows | Select-Object -ExpandProperty email -Unique).Count
    $verifiedCount = (@($rows | Where-Object { $_.verified_email } | Select-Object -ExpandProperty email -Unique)).Count
    $sources = (($rows | Select-Object -ExpandProperty source -Unique) -join "+")
    $countries = (($rows | Group-Object country | Sort-Object Count -Descending | Select-Object -First 3 | ForEach-Object { "$($_.Name) ($($_.Count))" }) -join "; ")
    $titles = (($rows | Where-Object title | Group-Object title_segment | Sort-Object Count -Descending | Select-Object -First 3 | ForEach-Object { "$($_.Name) ($($_.Count))" }) -join "; ")
    $industries = (($rows | Where-Object industry_segment | Group-Object industry_segment | Sort-Object Count -Descending | Select-Object -First 2 | ForEach-Object { "$($_.Name) ($($_.Count))" }) -join "; ")
    $sizes = (($rows | Group-Object size | Sort-Object Count -Descending | Select-Object -First 2 | ForEach-Object { "$($_.Name) ($($_.Count))" }) -join "; ")
    $companyScore = [Math]::Round((($rows | Measure-Object cp_fit_score -Average).Average * 0.4) + (($rows | Measure-Object cp_fit_score -Maximum).Maximum * 0.6) + [Math]::Min($emailCount,5), 1)
    [pscustomobject]@{
        company = $top.company
        domain = $top.domain
        source = $sources
        recommended_segment = $top.industry_segment
        predominant_country = $top.country
        predominant_size = $top.size
        contacts_with_email = $emailCount
        verified_emails = $verifiedCount
        top_role_segments = $titles
        industry_evidence = $industries
        country_evidence = $countries
        size_evidence = $sizes
        sample_contact = $top.contact
        sample_title = $top.title
        sample_email = $top.email
        website = $top.website
        score_conprospeccion = $companyScore
        duplicate_contact_rows = $rows.Count
    }
}

$recommended = $companies |
    Where-Object { $_.recommended_segment -ne "Otros sectores" -and $_.contacts_with_email -ge 1 -and $_.score_conprospeccion -ge 55 } |
    Sort-Object score_conprospeccion, contacts_with_email -Descending

$recommended | Export-Csv -NoTypeInformation -Encoding UTF8 -Path (Join-Path $outDir "empresas_recomendadas_conprospeccion.csv")

function Table-Lines($items, $cols) {
    $items | Select-Object $cols | ConvertTo-Csv -NoTypeInformation | ForEach-Object { $_ }
}

$totalRows = $all.Count
$totalEmail = $withEmail.Count
$totalCompanies = $companies.Count
$recommendedCompanies = @($recommended).Count
$duplicateCompanyGroups = @($companyGroups | Where-Object { $_.Count -gt 1 }).Count

$industryStats = $withEmail | Group-Object industry_segment | ForEach-Object {
    $rows = @($_.Group)
    [pscustomobject]@{
        segmento = $_.Name
        contactos_email = $rows.Count
        empresas = (@($rows | Group-Object { if ($_.domain) { $_.domain } else { $_.company_key } })).Count
        score_promedio = [Math]::Round((($rows | Measure-Object cp_fit_score -Average).Average),1)
        email_verificado_pct = [Math]::Round(((@($rows | Where-Object verified_email).Count / [Math]::Max($rows.Count,1))*100),1)
    }
} | Sort-Object contactos_email -Descending

$sizeStats = $withEmail | Group-Object size | Sort-Object Count -Descending | ForEach-Object { [pscustomobject]@{tamano=$_.Name; contactos_email=$_.Count} }
$countryStats = $withEmail | Group-Object country | Sort-Object Count -Descending | Select-Object -First 20 | ForEach-Object { [pscustomobject]@{pais=$_.Name; contactos_email=$_.Count} }
$roleStats = $withEmail | Group-Object title_segment | Sort-Object Count -Descending | ForEach-Object { [pscustomobject]@{cargo_segmento=$_.Name; contactos_email=$_.Count} }
$dups = $companies | Where-Object { $_.duplicate_contact_rows -gt 1 } | Sort-Object duplicate_contact_rows -Descending | Select-Object -First 20 company,domain,source,duplicate_contact_rows,contacts_with_email,recommended_segment

$topSegments = $recommended | Group-Object recommended_segment | ForEach-Object {
    $rows = @($_.Group)
    [pscustomobject]@{
        segmento = $_.Name
        empresas_recomendadas = $rows.Count
        contactos_email = (($rows | Measure-Object contacts_with_email -Sum).Sum)
        score_promedio = [Math]::Round((($rows | Measure-Object score_conprospeccion -Average).Average),1)
        paises_principales = (($rows | Group-Object predominant_country | Sort-Object Count -Descending | Select-Object -First 3 | ForEach-Object { "$($_.Name) ($($_.Count))" }) -join "; ")
        tamano_predominante = (($rows | Group-Object predominant_size | Sort-Object Count -Descending | Select-Object -First 1).Name)
    }
} | Sort-Object score_promedio, empresas_recomendadas -Descending | Select-Object -First 10

$campaigns = @(
    [pscustomobject]@{campana="Prospeccion para empresas tech y SaaS"; segmento="Tecnologia, SaaS y servicios IT"; motivo="Alto dolor de crecimiento outbound, ciclos B2B y uso natural de datos comerciales."},
    [pscustomobject]@{campana="Leads listos para agencias B2B"; segmento="Marketing, agencias y medios"; motivo="Agencias venden crecimiento y necesitan bases por nicho para clientes o nuevas cuentas."},
    [pscustomobject]@{campana="Inteligencia comercial para consultoras B2B"; segmento="Consultoria y servicios B2B"; motivo="Servicios de alto ticket con necesidad constante de prospeccion dirigida."},
    [pscustomobject]@{campana="Bases verificadas para fintech, factoring y seguros"; segmento="Finanzas, fintech y seguros"; motivo="Mercados con equipos comerciales activos y compra frecuente de data por vertical."},
    [pscustomobject]@{campana="Prospeccion para RRHH y recruiting"; segmento="RRHH, staffing y reclutamiento"; motivo="Necesitan identificar empresas contratantes y decisores por cargo e industria."}
)

$report = New-Object System.Collections.Generic.List[string]
$report.Add("# Informe ejecutivo - Campanas Conprospeccion")
$report.Add("")
$report.Add("Fecha de analisis: $(Get-Date -Format 'yyyy-MM-dd HH:mm')")
$report.Add("")
$report.Add("## Fuentes usadas")
$report.Add("- Apollo enriquecido: " + $apolloPath)
$report.Add("- Snov enriquecido: " + $snovPath)
$report.Add("")
$report.Add("## Resumen")
$report.Add("- Registros analizados: $totalRows")
$report.Add("- Contactos con email valido: $totalEmail")
$report.Add("- Empresas consolidadas con email: $totalCompanies")
$report.Add("- Empresas recomendadas: $recommendedCompanies")
$report.Add("- Grupos de empresa/dominio duplicados: $duplicateCompanyGroups")
$report.Add("")
$report.Add("## Industrias con mas registros con email")
$report.Add('```csv')
Table-Lines ($industryStats | Select-Object -First 15) @("segmento","contactos_email","empresas","score_promedio","email_verificado_pct") | ForEach-Object { $report.Add($_) }
$report.Add('```')
$report.Add("")
$report.Add("## Tamano de empresa predominante")
$report.Add('```csv')
Table-Lines $sizeStats @("tamano","contactos_email") | ForEach-Object { $report.Add($_) }
$report.Add('```')
$report.Add("")
$report.Add("## Paises disponibles")
$report.Add('```csv')
Table-Lines $countryStats @("pais","contactos_email") | ForEach-Object { $report.Add($_) }
$report.Add('```')
$report.Add("")
$report.Add("## Cargos disponibles")
$report.Add('```csv')
Table-Lines $roleStats @("cargo_segmento","contactos_email") | ForEach-Object { $report.Add($_) }
$report.Add('```')
$report.Add("")
$report.Add("## Empresas duplicadas principales")
$report.Add('```csv')
Table-Lines $dups @("company","domain","source","duplicate_contact_rows","contacts_with_email","recommended_segment") | ForEach-Object { $report.Add($_) }
$report.Add('```')
$report.Add("")
$report.Add("## Top 10 segmentos recomendados")
$report.Add('```csv')
Table-Lines $topSegments @("segmento","empresas_recomendadas","contactos_email","score_promedio","paises_principales","tamano_predominante") | ForEach-Object { $report.Add($_) }
$report.Add('```')
$report.Add("")
$report.Add("## Top 5 campanas para lanzar inmediatamente")
$report.Add('```csv')
Table-Lines $campaigns @("campana","segmento","motivo") | ForEach-Object { $report.Add($_) }
$report.Add('```')
$report.Add("")
$report.Add("## Criterio de recomendacion")
$report.Add("Se priorizaron empresas con email valido, cargos comerciales/gerenciales/marketing, industrias donde la compra de bases e inteligencia comercial es una necesidad directa, paises LATAM accionables y tamanos 11-500 empleados. El CSV final esta deduplicado por dominio cuando existe, o por nombre normalizado de empresa.")

$reportPath = Join-Path $outDir "informe_ejecutivo_conprospeccion.md"
$report | Set-Content -Encoding UTF8 -Path $reportPath

[pscustomobject]@{
    output_dir = $outDir
    report = $reportPath
    recommended_csv = Join-Path $outDir "empresas_recomendadas_conprospeccion.csv"
    records_analyzed = $totalRows
    contacts_with_email = $totalEmail
    companies_with_email = $totalCompanies
    recommended_companies = $recommendedCompanies
} | ConvertTo-Json -Depth 4 | Set-Content -Encoding UTF8 -Path (Join-Path $outDir "resumen_analisis.json")

Write-Host "Listo: $outDir"

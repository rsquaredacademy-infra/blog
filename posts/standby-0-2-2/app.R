# Lumaquill store dashboard. All data is simulated.
# The app behind the screenshots in this post. Run with shiny::runApp("app.R").
library(shiny)
library(standby)

set.seed(2026)  # same first view every run

make_sales <- function() {
  data.frame(
    store   = c("Northgate", "Riverside", "Harbourside", "Elm Park", "Old Mill"),
    revenue = round(runif(5, 40, 120)) * 1000,
    orders  = as.integer(round(runif(5, 300, 900)))
  )
}

ui <- fluidPage(
  useThreeDots(), useSpinkit(), useLoaders(), useToast(), useNotify(), useMicroTip(),
  # a steady box for each panel, so a loader waits where the data will appear
  tags$style(".standby { min-height: 260px; }"),
  titlePanel("Lumaquill - store sales"),
  div(id = "kpi", style = "font-size:28px; margin:10px 0;",
      textOutput("total", inline = TRUE)),
  actionButton("refresh", "Refresh data"),
  actionButton("bad", "Refresh (store feed down)"),
  actionButton("close_day", "Close day"),
  br(), br(),
  div(id = "row-colours",
    fluidRow(
      column(6,
        h4("Sales by store"),
        threeDots(tableOutput("sales"), type = "flashing", color = "#c2410c")
      ),
      column(6,
        h4("Revenue by store"),
        threeDots(plotOutput("revenue_chart", height = "240px"),
                  type = "flashing", color = "#0f766e")
      )
    )
  ),
  div(id = "row-spinkit",
    fluidRow(
      column(6,
        h4("Open orders"),
        spinkit(tableOutput("open_orders"), type = "swing",
                color = "rgba(37, 99, 235, 0.45)")
      ),
      column(6,
        h4("Stock cover"),
        spinkit(plotOutput("stock", height = "240px"), type = "wander",
                color = "rgba(37, 99, 235, 0.45)")
      )
    )
  ),
  # The music loader covers the screen, so the panel is built when it runs.
  uiOutput("close_panel"),
  br(), br()
)

server <- function(input, output, session) {

  microTip(id = "kpi", tip = "Revenue booked today across the five stores",
           position = "bottom")

  # The five stores, refreshed on demand; the first view is the seeded one.
  sales <- eventReactive(input$refresh, make_sales(), ignoreNULL = FALSE)

  observeEvent(input$bad, {
    notify("Refresh failed", "Could not reach the Harbourside feed.", type = "error")
  })

  output$sales <- renderTable({
    d <- sales()
    Sys.sleep(3)                       # pretend the warehouse query is slow
    if (input$refresh > 0)
      notify("Data refreshed", "Sales are up to date.", type = "success")
    d$revenue <- format(d$revenue, big.mark = ",")
    d
  }, align = "lrr")

  output$revenue_chart <- renderPlot({
    d <- sales()
    Sys.sleep(2)
    barplot(setNames(d$revenue / 1000, d$store), col = "#0f766e", border = NA,
            ylab = "Revenue (thousands)", cex.names = 0.9)
  })

  output$open_orders <- renderTable({
    d <- sales()
    Sys.sleep(2)
    data.frame(
      store  = d$store,
      open   = round(d$orders * 0.12),
      oldest = c("2 h", "5 h", "1 d", "3 h", "6 h")
    )
  }, align = "lrr")

  output$stock <- renderPlot({
    d <- sales()
    Sys.sleep(2)
    barplot(setNames(round(d$orders / 40), d$store), col = "#2563eb", border = NA,
            ylab = "Days of cover", cex.names = 0.9)
  })

  output$total <- renderText({
    paste("Revenue:", format(sum(sales()$revenue), big.mark = ","))
  })

  # Closing the day settles today's orders, then reports the total.
  output$close_panel <- renderUI({
    if (is.null(input$close_day) || input$close_day == 0) return(NULL)
    div(id = "row-close",
      fluidRow(
        column(6,
          h4("Day close"),
          loaders(tableOutput("day_close"), type = "music")
        )
      )
    )
  })

  output$day_close <- renderTable({
    d <- sales()
    Sys.sleep(3.5)                     # the settlement run
    toast(
      "Day closed",
      paste(format(sum(d$orders), big.mark = ","), "orders settled,",
            format(sum(d$revenue), big.mark = ","), "in takings."),
      type = "success", position = "topCenter"
    )
    data.frame(
      store   = d$store,
      orders  = d$orders,
      takings = format(d$revenue, big.mark = ",")
    )
  }, align = "lrr")
}

shinyApp(ui, server)

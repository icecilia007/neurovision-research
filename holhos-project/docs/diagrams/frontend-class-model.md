# Frontend class model (high-level)

```mermaid
classDiagram

class main_page {
  <<page_route>>
}
class respond_questionnaire_page {
  <<page_route>>
}
class questionnaire_answer_page {
  <<page_function>>
}
class clear_and_render {
  <<function>>
}

class AuthPage {
  <<page>>
}
class DashboardPage {
  <<page>>
}
class ReportsPage {
  <<page>>
}
class QuestionnaireListPage {
  <<page>>
}
class QuestionnaireDetailedReport {
  <<page>>
}
class QuestionnaireAnalyticsReport {
  <<page>>
}
class QuestionnaireAnswerPage {
  <<page>>
}
class questionnaire_create_page {
  <<page_function>>
}

class AuthModal {
  <<component>>
}
class LoginForm {
  <<component>>
}
class SignupForm {
  <<component>>
}
class QuestionItemEditor {
  <<component>>
}
class QuestionComponent {
  <<component>>
}
class SortableColumn {
  <<component>>
}
class SummaryCards {
  <<component>>
}
class BarChartCard {
  <<component>>
}
class PieChartCard {
  <<component>>
}
class CrosstabTool {
  <<component>>
}
class FilterSidebar {
  <<component>>
}
class ReliabilityCard {
  <<component>>
}
class SubscaleSection {
  <<component>>
}
class ExportButtons {
  <<component>>
}
class TextResponsesTable {
  <<component>>
}

class Config {
  <<config>>
}
class APIClient {
  <<service>>
}
class UserService {
  <<service>>
}
class QuestionnaireService {
  <<service>>
}
class QuestionClient {
  <<service>>
}
class InstructionClient {
  <<service>>
}
class ReportService {
  <<service>>
}
class AnalyticsService {
  <<service>>
}
class ResponseService {
  <<service>>
}

class SessionManager {
  <<util>>
}
class Validators {
  <<util>>
}
class PlotlyConfig {
  <<module>>
}
class Router {
  <<module>>
}

main_page ..> AuthPage
main_page ..> DashboardPage
main_page ..> SessionManager
main_page ..> Config

Router ..> clear_and_render
Router ..> respond_questionnaire_page
respond_questionnaire_page ..> questionnaire_answer_page
questionnaire_answer_page ..> QuestionnaireAnswerPage

AuthPage ..> LoginForm
AuthPage ..> SignupForm
AuthModal ..> LoginForm
AuthModal ..> SignupForm
LoginForm ..> UserService
LoginForm ..> Validators
LoginForm ..> SessionManager
SignupForm ..> UserService
SignupForm ..> Validators

DashboardPage ..> ReportsPage
DashboardPage ..> QuestionnaireListPage
DashboardPage ..> SessionManager
DashboardPage ..> Router

QuestionnaireListPage ..> QuestionnaireService
QuestionnaireListPage ..> questionnaire_create_page
QuestionnaireListPage ..> SessionManager
QuestionnaireListPage ..> Router

questionnaire_create_page ..> QuestionItemEditor
questionnaire_create_page ..> SortableColumn
questionnaire_create_page ..> InstructionClient
questionnaire_create_page ..> QuestionClient
questionnaire_create_page ..> QuestionnaireService
questionnaire_create_page ..> APIClient
questionnaire_create_page ..> SessionManager

QuestionnaireAnswerPage ..> QuestionnaireService
QuestionnaireAnswerPage ..> ResponseService
QuestionnaireAnswerPage ..> AuthModal

ReportsPage ..> QuestionnaireService
ReportsPage ..> ReportService
ReportsPage ..> QuestionnaireDetailedReport
ReportsPage ..> QuestionnaireAnalyticsReport
ReportsPage ..> SessionManager
ReportsPage ..> Router

QuestionnaireDetailedReport ..> ReportService
QuestionnaireDetailedReport ..> AnalyticsService
QuestionnaireDetailedReport ..> SummaryCards
QuestionnaireDetailedReport ..> PieChartCard
QuestionnaireDetailedReport ..> BarChartCard
QuestionnaireDetailedReport ..> SubscaleSection
QuestionnaireDetailedReport ..> CrosstabTool
QuestionnaireDetailedReport ..> ReliabilityCard
QuestionnaireDetailedReport ..> ExportButtons
QuestionnaireDetailedReport ..> FilterSidebar
QuestionnaireDetailedReport ..> PlotlyConfig

QuestionnaireAnalyticsReport ..> ReportService

BarChartCard ..> PlotlyConfig
PieChartCard ..> PlotlyConfig
SubscaleSection ..> PlotlyConfig

ExportButtons ..> ReportService

QuestionItemEditor ..> SortableColumn

UserService ..> APIClient
QuestionnaireService ..> APIClient
QuestionClient ..> APIClient
InstructionClient ..> APIClient
ReportService ..> APIClient
AnalyticsService ..> APIClient
ResponseService ..> APIClient
APIClient ..> Config
```

Notes:
- This diagram is a high-level view of the frontend modules, pages, and UI components.
- The page entry point is defined in app.py using NiceGUI and routes in router.py.
- questionnaire_create_page and questionnaire_answer_page are page-level functions rather than classes.

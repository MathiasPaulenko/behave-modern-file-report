Feature: Sample feature for behave-modern-file-reports

  This feature demonstrates passed, failed, and skipped scenarios
  to showcase the report formatters.

  @smoke
  Scenario: Successful scenario
    Given a passing step
    When I do something successfully
    Then I should see the result

  @regression
  Scenario: Failing scenario
    Given a passing step
    When I do something that fails
    Then I should see an error

  @skip
  Scenario: Skipped scenario
    Given a passing step
    When I do something that is skipped
    Then I should not reach this step

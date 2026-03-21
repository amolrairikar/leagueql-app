Feature: Onboard fantasy football league

    @writes_data
    Scenario: Successfully onboard ESPN league
        Given a valid set of ESPN league inputs
        When we run the onboarding lambda
        Then the lambda will complete successfully
        And the lambda response object status code will be 200
        And the DynamoDB table will contain 3 items

    Scenario: Invalid league ID while onboarding ESPN league
        Given a invalid set of ESPN league inputs
        When we run the onboarding lambda
        Then the lambda will complete successfully
        And the lambda response object status code will be 502
        And the DynamoDB table will contain 0 items

    @writes_data
    Scenario: Successfully onboard SLEEPER league
        Given a valid set of SLEEPER league inputs
        When we run the onboarding lambda
        Then the lambda will complete successfully
        And the lambda response object status code will be 200
        And the DynamoDB table will contain 3 items

    Scenario: Invalid league ID while onboarding SLEEPER league
        Given a invalid set of SLEEPER league inputs
        When we run the onboarding lambda
        Then the lambda will complete successfully
        And the lambda response object status code will be 502
        And the DynamoDB table will contain 0 items
Feature: Unused league reaper (backend/league-reaper)
  The nightly Lambda removes leagues nobody has opened for a calendar year, from both
  DynamoDB and S3, and is a dry run unless deletion is explicitly enabled.

  Background:
    Given an idle "YAHOO" league "canon-idle" with views, a lookup, a member, and raw data
    And an active league "canon-active" that was onboarded long ago but opened recently
    And a YAHOO_OAUTH token item exists for the default user

  Scenario: An idle league is removed entirely and active leagues are kept
    When the league reaper runs with deletion enabled
    Then nothing remains of league "canon-idle"
    And a METADATA item still exists for league "canon-active"
    And league "canon-active" still has raw data in S3
    And no YAHOO_OAUTH token item exists for the default user
    And the reaper summary reports 1 under "Removed"

  Scenario: A dry run changes nothing
    When the league reaper runs as a dry run
    Then a METADATA item still exists for league "canon-idle"
    And league "canon-idle" still has raw data in S3
    And a YAHOO_OAUTH token item exists for the default user afterwards
    And the reaper summary reports 1 under "Would remove"

  Scenario: Several idle leagues of one owner still clean up their credentials
    Given an idle "YAHOO" league "canon-idle-2" with views, a lookup, a member, and raw data
    When the league reaper runs with deletion enabled
    Then nothing remains of league "canon-idle"
    And nothing remains of league "canon-idle-2"
    And no YAHOO_OAUTH token item exists for the default user

  Scenario: A league with a job in progress is skipped
    Given the idle league "canon-idle" has a job in progress
    When the league reaper runs with deletion enabled
    Then a METADATA item still exists for league "canon-idle"
    And the reaper summary reports 1 under "Skipped (busy)"

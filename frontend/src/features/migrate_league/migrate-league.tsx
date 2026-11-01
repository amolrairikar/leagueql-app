import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Step1 } from '@/features/migrate_league/step1-confirm-league';
import { Step2 } from '@/features/migrate_league/step2-new-platform-setup';
import { Step3 } from '@/features/migrate_league/step3-map-managers';
import { Step4 } from '@/features/migrate_league/step4-preview-confirm';
import { Step5 } from '@/features/migrate_league/step5-migrating';
import { type WizardStep } from '@/features/migrate_league/types';
import { useMigrationWizard } from '@/features/migrate_league/use-migration-wizard';

export default function MigrateLeague() {
  const {
    leagueId,
    platform,
    seasons,
    step,
    setStep,
    leagueName,
    currentManagers,
    newPlatformInfo,
    setNewPlatformInfo,
    newPlatformUsers,
    setNewPlatformUsers,
    managerMapping,
    setManagerMapping,
    isSubmitting,
    submitError,
    pollOutcome,
    operationId,
    failureReason,
    resumeDestId,
    resumeNotice,
    handleConfirm,
  } = useMigrationWizard();

  const stepTitles: Record<WizardStep, string> = {
    1: 'Confirm Current League',
    2: 'New Platform Setup',
    3: 'Map Managers',
    4: 'Preview & Confirm',
    5: 'Migrating…',
  };

  return (
    <div className="min-h-screen bg-background text-foreground font-sans overflow-x-hidden">
      <div
        className="fixed inset-0 pointer-events-none z-0"
        style={{
          backgroundImage: `
            linear-gradient(var(--border) 1px, transparent 1px),
            linear-gradient(90deg, var(--border) 1px, transparent 1px)
          `,
          backgroundSize: '48px 48px',
          opacity: 0.2,
        }}
      />

      <div className="relative z-10 flex items-center justify-center min-h-screen">
        <Card className="w-full max-w-lg">
          <CardHeader>
            <div className="flex items-center gap-2 mb-1">
              {([1, 2, 3, 4] as WizardStep[]).map((s) => (
                <div
                  key={s}
                  className={`h-1 flex-1 rounded-full transition-colors ${
                    s <= step ? 'bg-primary' : 'bg-muted'
                  }`}
                />
              ))}
            </div>
            <CardTitle className="text-xl text-center font-bold">
              {stepTitles[step]}
            </CardTitle>
            {step < 5 && (
              <p className="text-[12px] text-center text-muted-foreground">
                Step {step} of 4
              </p>
            )}
          </CardHeader>
          <CardContent>
            {step === 1 && (
              <Step1
                leagueId={leagueId}
                platform={platform}
                seasons={seasons}
                leagueName={leagueName}
                onNext={() => setStep(2)}
              />
            )}
            {step === 2 && (
              <Step2
                currentPlatform={platform}
                currentLeagueId={leagueId}
                initialDestination={resumeDestId ? 'YAHOO' : undefined}
                initialLeagueId={resumeDestId || undefined}
                initialNotice={resumeNotice ?? undefined}
                onNext={(info, users) => {
                  setNewPlatformInfo(info);
                  setNewPlatformUsers(users);
                  setStep(3);
                }}
                onBack={() => setStep(1)}
              />
            )}
            {step === 3 && newPlatformInfo && (
              <Step3
                currentManagers={currentManagers}
                newPlatformUsers={newPlatformUsers}
                newPlatform={newPlatformInfo.newPlatform}
                onNext={(mapping) => {
                  setManagerMapping(mapping);
                  setStep(4);
                }}
                onBack={() => setStep(2)}
              />
            )}
            {step === 4 && newPlatformInfo && (
              <Step4
                currentSeasons={seasons}
                newPlatform={newPlatformInfo.newPlatform}
                newPlatformLeagueId={newPlatformInfo.newPlatformLeagueId}
                newSeason={newPlatformInfo.season}
                totalManagers={currentManagers.length}
                mappedManagers={managerMapping.length}
                isSubmitting={isSubmitting}
                submitError={submitError}
                onConfirm={() => void handleConfirm()}
                onBack={() => setStep(3)}
              />
            )}
            {step === 5 && (
              <Step5
                pollOutcome={pollOutcome}
                operationId={operationId}
                failureReason={failureReason}
              />
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

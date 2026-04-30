import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';

interface AboutDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function AboutDialog({ open, onOpenChange }: AboutDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle className="text-2xl font-bold">About</DialogTitle>
        </DialogHeader>
        <p>
          Welcome to LeagueQL! This app is designed to provide insightful analytics for your fantasy football league.
          <br />
          <br />
          The source code can be found on{' '}
          <a
            href="https://github.com/amolrairikar/leagueql-app"
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-500 hover:underline"
          >
            GitHub
          </a>
          . You can report any bugs or request new features there using the corresponding forms.
          <br />
          <br />
          My goal is to always keep this app free and ad-free. However, there are costs associated with hosting and
          maintaining the app. If you find this app useful and would like to support its development, you can donate
          using the link below.
          <br />
          <br />
          <a
            href="https://www.buymeacoffee.com/amolrairikar"
            target="_blank"
            rel="noopener noreferrer"
            className="flex justify-center"
          >
            <img
              src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png"
              alt="Buy Me A Coffee"
              style={{ height: '60px', width: '217px' }}
            />
          </a>
        </p>
      </DialogContent>
    </Dialog>
  );
}

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
          Welcome to LeagueQL! This app is designed to help you answer questions
          about your fantasy football league such as:
          <br />
          <br />
          <span className="block pl-4">
            • Which player has scored the most fantasy football points in a
            single game?
          </span>
          <span className="block pl-4">
            • What is my all-time head-to-head record against each opponent?
          </span>
          <span className="block pl-4">
            • Who could I have drafted instead of my current roster?
          </span>
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
          . If you encounter any bugs, please report them there using the issues
          section.
          <br />
          <br />
          Have a feature request? Add your idea to the board{' '}
          <a
            href="https://leagueql.supahub.com/en"
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-500 hover:underline"
          >
            here
          </a>
          .
          <br />
          <br />
          My goal is to keep this app free. However, there are costs associated
          with hosting and maintaining the app and there may be a subscription
          model in the future.
        </p>
      </DialogContent>
    </Dialog>
  );
}

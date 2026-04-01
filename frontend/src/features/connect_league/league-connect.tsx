import { useState } from 'react';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

export default function LeagueConnect() {
  const [platform, setPlatform] = useState<string>('');

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
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle className="text-2xl text-center font-bold">
              Connect League
            </CardTitle>
          </CardHeader>
          <CardContent>
            <form className="flex flex-col gap-4">
              <div className="flex flex-col gap-2">
                <Label htmlFor="platform">Platform</Label>
                <Select onValueChange={setPlatform}>
                  <SelectTrigger id="platform" className="w-full">
                    <SelectValue placeholder="Select a platform" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="espn">ESPN</SelectItem>
                    <SelectItem value="sleeper">Sleeper</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="flex flex-col gap-2">
                <Label htmlFor="league-id">League ID</Label>
                <Input
                  id="league-id"
                  type="text"
                  placeholder="Enter your league ID"
                />
              </div>
              {platform === 'espn' && (
                <div className="flex flex-col gap-2">
                  <Label htmlFor="latest-season">Latest Season</Label>
                  <Input
                    id="latest-season"
                    type="text"
                    placeholder="Enter the latest season"
                  />
                </div>
              )}
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

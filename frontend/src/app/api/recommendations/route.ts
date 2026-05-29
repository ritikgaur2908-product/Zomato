import { NextResponse } from "next/server";
import { spawn } from "child_process";
import path from "path";

export async function POST(request: Request): Promise<Response> {
  try {
    const body = await request.json();
    const {
      location,
      budget = "medium",
      cuisine = [],
      min_rating = 0.0,
      top_n = 5,
      extras = "",
    } = body;

    if (!location) {
      return NextResponse.json(
        { error: "Location is required" },
        { status: 400 }
      );
    }

    // Check if we should call a remote API instead of local spawn (useful for Vercel/production)
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_API_URL;
    if (backendUrl) {
      try {
        console.log(`Forwarding recommendations request to remote backend API: ${backendUrl}`);
        const response = await fetch(`${backendUrl}/recommend`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            location,
            budget,
            cuisine: Array.isArray(cuisine) ? cuisine : [cuisine],
            min_rating: Number(min_rating),
            top_n: Number(top_n),
            extras,
          }),
        });

        if (!response.ok) {
          const responseText = await response.text().catch(() => "");
          console.error(`Remote API error (${response.status}):`, responseText);
          let detail = "";
          try {
            const parsed = JSON.parse(responseText);
            detail = parsed.detail || parsed.message || "";
          } catch (e) {
            detail = responseText.substring(0, 150);
          }
          return NextResponse.json(
            { error: detail || `Remote server error (status ${response.status})` },
            { status: response.status }
          );
        }

        const data = await response.json();
        return NextResponse.json(data);
      } catch (err: any) {
        console.error("Failed to connect to remote backend API:", err);
        return NextResponse.json(
          { error: "Could not connect to remote recommendation engine", details: err?.message },
          { status: 502 }
        );
      }
    }

    // Resolve the workspace directory (which is the root where app/main.py is located)
    // The working directory should be the root of the Zomato repository.
    const projectRoot = path.resolve(process.cwd(), "..");

    const args = [
      "-m",
      "app.main",
      "--location",
      location,
      "--budget",
      budget,
      "--cuisine",
      Array.isArray(cuisine) ? cuisine.join(",") : cuisine,
      "--min-rating",
      String(min_rating),
      "--top-n",
      String(top_n),
      "--output-format",
      "json",
    ];

    if (extras && typeof extras === "string" && extras.trim()) {
      args.push("--extras", extras.trim());
    }

    return new Promise<Response>((resolve) => {
      // Spawn python with projectRoot as working directory and UTF-8 encoding forced
      const pythonProcess = spawn("python", args, {
        cwd: projectRoot,
        env: {
          ...process.env,
          PYTHONIOENCODING: "utf-8",
        },
      });

      let stdoutData = "";
      let stderrData = "";

      pythonProcess.stdout.on("data", (data) => {
        stdoutData += data.toString("utf-8");
      });

      pythonProcess.stderr.on("data", (data) => {
        stderrData += data.toString("utf-8");
      });

      pythonProcess.on("close", (code) => {
        if (code !== 0) {
          console.error(`Python process exited with code ${code}. Stderr: ${stderrData}`);
          
          // Check if it's a validation error or user-friendly message in stdout
          try {
            const parsed = JSON.parse(stdoutData);
            if (parsed && (parsed.error || parsed.message)) {
              return resolve(
                NextResponse.json(
                  { error: parsed.error || parsed.message, details: stderrData },
                  { status: 400 }
                )
              );
            }
          } catch (e) {
            // Not JSON
          }

          return resolve(
            NextResponse.json(
              { error: "Failed to generate recommendations", details: stderrData },
              { status: 500 }
            )
          );
        }

        try {
          const parsedResponse = JSON.parse(stdoutData);
          resolve(NextResponse.json(parsedResponse));
        } catch (error) {
          console.error("Failed to parse Python JSON output:", stdoutData, error);
          resolve(
            NextResponse.json(
              { error: "Invalid response from recommendation engine", raw: stdoutData },
              { status: 500 }
            )
          );
        }
      });
    });
  } catch (error: any) {
    console.error("API error:", error);
    return NextResponse.json(
      { error: error?.message || "Internal server error" },
      { status: 500 }
    );
  }
}

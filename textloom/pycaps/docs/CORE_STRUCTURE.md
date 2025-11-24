# Core Concepts & Structure

To effectively use `pycaps` as a library, it's important to understand its underlying data structure. The entire subtitle and video content is organized in a hierarchical model.

### The Data Hierarchy

The structure flows from the entire video down to a single word:

**`Document`** -> **`Segment`** -> **`Line`** -> **`Word`** -> **`WordClip`**

Here's what each level represents:

#### 1. `Document`
The `Document` is the top-level object. It represents the entire video's transcribed content.
-   It contains a list of `Segment` objects.
-   It also holds global elements like sound effects (`sfxs`) that will be added to the final video.

#### 2. `Segment`
A `Segment` is a logical unit of speech, typically a full sentence or a coherent phrase.
-   Initially, Whisper provides segments.
-   These can be further divided by `Splitters` (e.g., splitting a long sentence into multiple segments).
-   Each `Segment` contains one or more `Line` objects.

#### 3. `Line`
A `Line` represents a single line of text as it will appear on the screen.
-   Segments are broken down into `Lines` by the `LineSplitter` based on layout rules like `max_width_ratio` and `max_number_of_lines`.
-   Each `Line` contains one or more `Word` objects.

#### 4. `Word`
The `Word` is the most granular text element.
-   It holds the text of a single word and its start/end time from the transcription.
-   It is the primary target for `semantic_tags` (e.g., `highlight`) and `structure_tags` (e.g., `first-word-in-line`).

#### 5. `WordClip`
A `WordClip` is the actual renderable element. A single `Word` is represented by multiple `WordClip`s, each corresponding to a different visual state over time.

For example, the word "Hello" might be composed of three `WordClip`s:
1.  **"Not Narrated Yet"**: The clip of "Hello" that is visible before the speaker says it.
2.  **"Being Narrated"**: The clip that plays exactly when "Hello" is spoken (from `word.time.start` to `word.time.end`).
3.  **"Already Narrated"**: The clip of "Hello" that remains on screen after it has been spoken.

This separation allows you to apply different CSS styles and animations to each state. For instance, you can make the `.word-being-narrated` clip yellow and larger, while the others remain white.
const searchButton =
    document.getElementById("searchButton");

const requestInput =
    document.getElementById("request");

const quantityInput =
    document.getElementById("quantity");

const watermarkInput =
    document.getElementById("watermark");

const results =
    document.getElementById("results");

const status =
    document.getElementById("status");


let shorts = [];

let downloadedFiles = {};


// --------------------------------------------------
// GET WATERMARK
// --------------------------------------------------

function getWatermark() {

    return watermarkInput.value.trim();

}


// --------------------------------------------------
// GET SELECTED SHORTS
// --------------------------------------------------

function getSelectedShorts() {

    return shorts.filter(
        function (short) {

            const checkbox =
                document.getElementById(
                    `short-checkbox-${short.index}`
                );

            return (
                checkbox &&
                checkbox.checked
            );

        }
    );

}


// --------------------------------------------------
// UPDATE SELECTION CONTROLS
// --------------------------------------------------

function updateSelectionControls() {

    const selectedShorts =
        getSelectedShorts();

    const count =
        selectedShorts.length;

    const selectionInfo =
        document.getElementById(
            "selectionInfo"
        );

    const downloadSelectedButton =
        document.getElementById(
            "downloadSelectedButton"
        );

    const compileSelectedButton =
        document.getElementById(
            "compileSelectedButton"
        );

    if (selectionInfo) {

        selectionInfo.textContent =
            `${count} selected`;

    }

    if (downloadSelectedButton) {

        downloadSelectedButton.disabled =
            count < 1;

    }

    if (compileSelectedButton) {

        compileSelectedButton.disabled =
            count < 2;

    }

}


// --------------------------------------------------
// REFRESH DOWNLOADED FILES
// --------------------------------------------------

async function refreshDownloadedFiles() {

    try {

        const response =
            await fetch("/downloads");

        const data =
            await response.json();

        if (
            response.ok &&
            data.success
        ) {

            downloadedFiles = {};

            (data.files || []).forEach(
                function (filename) {

                    downloadedFiles[filename] =
                        true;

                }
            );

            updateDownloadedButtons();

        }

    }

    catch (error) {

        console.error(
            "Could not refresh downloaded files:",
            error
        );

    }

}


// --------------------------------------------------
// UPDATE DOWNLOADED BUTTONS
// --------------------------------------------------

function updateDownloadedButtons() {

    shorts.forEach(
        function (short) {

            const button =
                document.getElementById(
                    `download-button-${short.index}`
                );

            if (!button) {
                return;
            }

            if (
                short.downloadedFilename &&
                downloadedFiles[
                    short.downloadedFilename
                ]
            ) {

                button.textContent =
                    "DOWNLOADED ✓";

                button.dataset.downloaded =
                    "true";

            }

        }
    );

}


// --------------------------------------------------
// DOWNLOAD ONE SHORT
// --------------------------------------------------

async function downloadShort(
    short,
    button
) {

    button.disabled =
        true;

    button.textContent =
        "DOWNLOADING...";

    try {

        const watermark =
            getWatermark();

        const response =
            await fetch(
                "/download",
                {

                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({

                        url:
                            short.url,

                        watermark:
                            watermark

                    })

                }
            );

        if (!response.ok) {

            let errorMessage =
                "Download failed.";

            try {

                const errorData =
                    await response.json();

                errorMessage =
                    errorData.error ||
                    errorMessage;

            }

            catch (error) {
                // Ignore JSON parsing errors.
            }

            throw new Error(
                errorMessage
            );

        }

        const disposition =
            response.headers.get(
                "Content-Disposition"
            );

        let filename =
            null;

        if (disposition) {

            const match =
                disposition.match(
                    /filename="?([^"]+)"?/i
                );

            if (match) {

                filename =
                    match[1];

            }

        }

        const blob =
            await response.blob();

        const blobUrl =
            window.URL.createObjectURL(
                blob
            );

        const link =
            document.createElement("a");

        link.href =
            blobUrl;

        link.download =
            filename ||
            "short.mp4";

        document.body.appendChild(
            link
        );

        link.click();

        link.remove();

        window.URL.revokeObjectURL(
            blobUrl
        );

        if (filename) {

            short.downloadedFilename =
                filename;

        }

        short.downloadedWithWatermark =
            watermark;

        button.textContent =
            "DOWNLOADED ✓";

        button.dataset.downloaded =
            "true";

        return {
            success: true,
            filename: filename
        };

    }

    catch (error) {

        console.error(
            "Download error:",
            error
        );

        button.textContent =
            "DOWNLOAD FAILED";

        throw error;

    }

    finally {

        button.disabled =
            false;

    }

}


// --------------------------------------------------
// DOWNLOAD SELECTED IN PARALLEL
// --------------------------------------------------

async function downloadSelected() {

    const selectedShorts =
        getSelectedShorts();

    if (selectedShorts.length < 1) {

        alert(
            "Select at least one Short first."
        );

        return;

    }

    const button =
        document.getElementById(
            "downloadSelectedButton"
        );

    button.disabled =
        true;

    button.textContent =
        "DOWNLOADING...";

    const startTime =
        performance.now();

    const watermark =
        getWatermark();

    try {

        const shortsToDownload =
            selectedShorts.filter(
                function (short) {

                    return !(
                        short.downloadedFilename &&
                        downloadedFiles[
                            short.downloadedFilename
                        ]
                    );

                }
            );

        const alreadyDownloaded =
            selectedShorts.length -
            shortsToDownload.length;

        if (
            shortsToDownload.length === 0
        ) {

            status.textContent =
                "All selected Shorts are already downloaded. ✓";

            return;

        }

        /*
         * Run up to 3 downloads at once.
         *
         * This is much faster than downloading
         * every Short one-by-one.
         */

        const MAX_CONCURRENT =
            3;

        let nextIndex =
            0;

        let completed =
            alreadyDownloaded;

        let failed =
            0;

        async function worker() {

            while (true) {

                const currentIndex =
                    nextIndex++;

                if (
                    currentIndex >=
                    shortsToDownload.length
                ) {

                    return;

                }

                const short =
                    shortsToDownload[
                        currentIndex
                    ];

                const individualButton =
                    document.getElementById(
                        `download-button-${short.index}`
                    );

                completed++;

                status.textContent =
                    `Downloading Shorts... ${completed}/${selectedShorts.length}`;

                try {

                    if (individualButton) {

                        await downloadShort(
                            short,
                            individualButton
                        );

                    }

                }

                catch (error) {

                    failed++;

                    console.error(
                        "Selected download failed:",
                        short.title,
                        error
                    );

                }

                completed++;

                status.textContent =
                    `Downloading Shorts... ${Math.min(
                        completed,
                        selectedShorts.length
                    )}/${selectedShorts.length}`;

            }

        }

        const workerCount =
            Math.min(
                MAX_CONCURRENT,
                shortsToDownload.length
            );

        const workers = [];

        for (
            let i = 0;
            i < workerCount;
            i++
        ) {

            workers.push(
                worker()
            );

        }

        await Promise.all(
            workers
        );

        await refreshDownloadedFiles();

        const elapsedSeconds =
            (
                performance.now() -
                startTime
            ) / 1000;

        if (failed > 0) {

            status.textContent =
                `Downloaded selected Shorts in ${elapsedSeconds.toFixed(
                    1
                )}s. ${failed} failed.`;

        }
        else {

            status.textContent =
                watermark
                    ? `Downloaded ${selectedShorts.length} selected Shorts with watermark in ${elapsedSeconds.toFixed(
                        1
                    )}s. ✓`
                    : `Downloaded ${selectedShorts.length} selected Shorts in ${elapsedSeconds.toFixed(
                        1
                    )}s. ✓`;

        }

    }

    catch (error) {

        console.error(
            "Selected download error:",
            error
        );

        status.textContent =
            "Selected download failed: " +
            error.message;

    }

    finally {

        button.disabled =
            false;

        button.textContent =
            "DOWNLOAD SELECTED";

        updateSelectionControls();

    }

}


// --------------------------------------------------
// COMPILE SELECTED + OPTIONAL WATERMARK
// --------------------------------------------------

async function compileSelected() {

    const selectedShorts =
        getSelectedShorts();

    if (selectedShorts.length < 2) {

        alert(
            "Select at least 2 Shorts to compile."
        );

        return;

    }

    const watermark =
        getWatermark();

    const compileButton =
        document.getElementById(
            "compileSelectedButton"
        );

    const downloadSelectedButton =
        document.getElementById(
            "downloadSelectedButton"
        );

    compileButton.disabled =
        true;

    downloadSelectedButton.disabled =
        true;

    compileButton.textContent =
        "PREPARING...";

    try {

        /*
         * First make sure every selected Short
         * is downloaded.
         *
         * This now uses parallel downloads.
         */

        const shortsToDownload =
            selectedShorts.filter(
                function (short) {

                    return !(
                        short.downloadedFilename &&
                        downloadedFiles[
                            short.downloadedFilename
                        ]
                    );

                }
            );

        if (
            shortsToDownload.length > 0
        ) {

            status.textContent =
                `Downloading ${shortsToDownload.length} selected Shorts...`;

            const MAX_CONCURRENT =
                3;

            let nextIndex =
                0;

            let completed =
                0;

            async function worker() {

                while (true) {

                    const currentIndex =
                        nextIndex++;

                    if (
                        currentIndex >=
                        shortsToDownload.length
                    ) {

                        return;

                    }

                    const short =
                        shortsToDownload[
                            currentIndex
                        ];

                    const individualButton =
                        document.getElementById(
                            `download-button-${short.index}`
                        );

                    status.textContent =
                        `Downloading selected Shorts...`;

                    try {

                        if (individualButton) {

                            await downloadShort(
                                short,
                                individualButton
                            );

                        }

                    }

                    catch (error) {

                        console.error(
                            "Download failed during compilation:",
                            short.title,
                            error
                        );

                    }

                    completed++;

                    status.textContent =
                        `Downloaded ${completed}/${shortsToDownload.length} new Shorts...`;

                }

            }

            const workerCount =
                Math.min(
                    MAX_CONCURRENT,
                    shortsToDownload.length
                );

            const workers = [];

            for (
                let i = 0;
                i < workerCount;
                i++
            ) {

                workers.push(
                    worker()
                );

            }

            await Promise.all(
                workers
            );

        }

        await refreshDownloadedFiles();

        const filesToCompile = [];

        /*
         * Preserve the exact order in which the
         * Shorts appear in the search results.
         */

        for (
            let i = 0;
            i < selectedShorts.length;
            i++
        ) {

            const short =
                selectedShorts[i];

            if (
                short.downloadedFilename &&
                downloadedFiles[
                    short.downloadedFilename
                ]
            ) {

                filesToCompile.push(
                    short.downloadedFilename
                );

            }

        }

        if (
            filesToCompile.length < 2
        ) {

            throw new Error(
                "Could not identify at least 2 downloaded Shorts."
            );

        }

        if (watermark) {

            status.textContent =
                `Compiling ${filesToCompile.length} Shorts with watermark...`;

        }
        else {

            status.textContent =
                `Compiling ${filesToCompile.length} Shorts without watermark...`;

        }

        compileButton.textContent =
            "COMPILING...";

        const compileStartTime =
            performance.now();

        const response =
            await fetch(
                "/compile",
                {

                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({

                        files:
                            filesToCompile,

                        watermark:
                            watermark

                    })

                }
            );

        if (!response.ok) {

            let errorMessage =
                "Compilation failed.";

            try {

                const errorData =
                    await response.json();

                errorMessage =
                    errorData.error ||
                    errorMessage;

            }

            catch (error) {
                // Ignore JSON parsing errors.
            }

            throw new Error(
                errorMessage
            );

        }

        const blob =
            await response.blob();

        const blobUrl =
            window.URL.createObjectURL(
                blob
            );

        const link =
            document.createElement("a");

        link.href =
            blobUrl;

        link.download =
            "shortbot_compilation.mp4";

        document.body.appendChild(
            link
        );

        link.click();

        link.remove();

        window.URL.revokeObjectURL(
            blobUrl
        );

        const compileElapsedSeconds =
            (
                performance.now() -
                compileStartTime
            ) / 1000;

        status.textContent =
            watermark
                ? `Compilation complete! ${filesToCompile.length} Shorts combined with watermark in ${compileElapsedSeconds.toFixed(
                    1
                )}s. ✓`
                : `Compilation complete! ${filesToCompile.length} Shorts combined in ${compileElapsedSeconds.toFixed(
                    1
                )}s. ✓`;

        compileButton.textContent =
            "COMPILED ✓";

    }

    catch (error) {

        console.error(
            "Compilation error:",
            error
        );

        status.textContent =
            "Compilation failed: " +
            error.message;

        compileButton.textContent =
            "COMPILE SELECTED";

        alert(
            "Could not compile the selected Shorts: " +
            error.message
        );

    }

    finally {

        downloadSelectedButton.disabled =
            false;

        updateSelectionControls();

    }

}


// --------------------------------------------------
// CREATE SELECTION CONTROLS
// --------------------------------------------------

function createSelectionControls() {

    const oldControls =
        document.getElementById(
            "selectionControls"
        );

    if (oldControls) {

        oldControls.remove();

    }

    const controls =
        document.createElement(
            "div"
        );

    controls.id =
        "selectionControls";

    const info =
        document.createElement(
            "div"
        );

    info.id =
        "selectionInfo";

    info.textContent =
        "0 selected";

    const downloadButton =
        document.createElement(
            "button"
        );

    downloadButton.id =
        "downloadSelectedButton";

    downloadButton.textContent =
        "DOWNLOAD SELECTED";

    downloadButton.disabled =
        true;

    downloadButton.addEventListener(
        "click",
        downloadSelected
    );

    const compileButton =
        document.createElement(
            "button"
        );

    compileButton.id =
        "compileSelectedButton";

    compileButton.textContent =
        "COMPILE SELECTED";

    compileButton.disabled =
        true;

    compileButton.addEventListener(
        "click",
        compileSelected
    );

    controls.appendChild(
        info
    );

    controls.appendChild(
        downloadButton
    );

    controls.appendChild(
        compileButton
    );

    results.appendChild(
        controls
    );

}


// --------------------------------------------------
// RENDER RESULTS
// --------------------------------------------------

function renderShorts(
    foundShorts
) {

    shorts =
        foundShorts.map(
            function (short, index) {

                return {
                    ...short,
                    index: index
                };

            }
        );

    shorts.forEach(
        function (short) {

            const card =
                document.createElement(
                    "div"
                );

            card.className =
                "short-card";

            const topRow =
                document.createElement(
                    "div"
                );

            topRow.style.display =
                "flex";

            topRow.style.alignItems =
                "flex-start";

            topRow.style.gap =
                "12px";

            const checkbox =
                document.createElement(
                    "input"
                );

            checkbox.type =
                "checkbox";

            checkbox.id =
                `short-checkbox-${short.index}`;

            checkbox.style.width =
                "20px";

            checkbox.style.height =
                "20px";

            checkbox.style.marginTop =
                "3px";

            checkbox.addEventListener(
                "change",
                updateSelectionControls
            );

            const title =
                document.createElement(
                    "h3"
                );

            title.textContent =
                `${short.index + 1}. ${short.title}`;

            title.style.margin =
                "0";

            topRow.appendChild(
                checkbox
            );

            topRow.appendChild(
                title
            );

            const buttons =
                document.createElement(
                    "div"
                );

            buttons.className =
                "short-buttons";

            const watchButton =
                document.createElement(
                    "a"
                );

            watchButton.href =
                short.url;

            watchButton.textContent =
                "WATCH SHORT";

            watchButton.target =
                "_blank";

            watchButton.rel =
                "noopener noreferrer";

            watchButton.className =
                "watch-button";

            const downloadButton =
                document.createElement(
                    "button"
                );

            downloadButton.id =
                `download-button-${short.index}`;

            downloadButton.textContent =
                "DOWNLOAD";

            downloadButton.className =
                "download-button";

            downloadButton.addEventListener(
                "click",
                async function () {

                    try {

                        await downloadShort(
                            short,
                            downloadButton
                        );

                        await refreshDownloadedFiles();

                        status.textContent =
                            getWatermark()
                                ? "Short downloaded with watermark successfully. ✓"
                                : "Short downloaded successfully. ✓";

                    }

                    catch (error) {

                        status.textContent =
                            "Download failed: " +
                            error.message;

                        alert(
                            "Could not download this Short: " +
                            error.message
                        );

                        setTimeout(
                            function () {

                                downloadButton.textContent =
                                    "DOWNLOAD";

                            },
                            2000
                        );

                    }

                }
            );

            buttons.appendChild(
                watchButton
            );

            buttons.appendChild(
                downloadButton
            );

            card.appendChild(
                topRow
            );

            card.appendChild(
                buttons
            );

            results.appendChild(
                card
            );

        }
    );

    createSelectionControls();

    refreshDownloadedFiles();

    updateSelectionControls();

}


// --------------------------------------------------
// SEARCH
// --------------------------------------------------

searchButton.addEventListener(
    "click",
    async function () {

        const userRequest =
            requestInput.value.trim();

        const quantity =
            Number(
                quantityInput.value
            );

        if (!userRequest) {

            status.textContent =
                "Please enter what Shorts you are looking for.";

            return;

        }

        if (
            !quantity ||
            quantity < 1
        ) {

            status.textContent =
                "Please enter a valid number of Shorts.";

            return;

        }

        shorts = [];

        downloadedFiles = {};

        document
            .querySelectorAll(
                ".short-card"
            )
            .forEach(
                function (card) {

                    card.remove();

                }
            );

        const oldControls =
            document.getElementById(
                "selectionControls"
            );

        if (oldControls) {

            oldControls.remove();

        }

        status.textContent =
            "Searching for Shorts...";

        searchButton.disabled =
            true;

        searchButton.textContent =
            "SEARCHING...";

        try {

            const response =
                await fetch(
                    "/search",
                    {

                        method: "POST",

                        headers: {
                            "Content-Type":
                                "application/json"
                        },

                        body: JSON.stringify({

                            request:
                                userRequest,

                            quantity:
                                quantity

                        })

                    }
                );

            const data =
                await response.json();

            if (
                !response.ok ||
                !data.success
            ) {

                throw new Error(
                    data.error ||
                    "Search failed."
                );

            }

            const foundShorts =
                data.results || [];

            if (
                foundShorts.length === 0
            ) {

                status.textContent =
                    "No relevant Shorts were found.";

                return;

            }

            status.textContent =
                `Found ${foundShorts.length} relevant Shorts.`;

            renderShorts(
                foundShorts
            );

        }

        catch (error) {

            console.error(
                "Search error:",
                error
            );

            status.textContent =
                "Something went wrong: " +
                error.message;

        }

        finally {

            searchButton.disabled =
                false;

            searchButton.textContent =
                "FIND SHORTS";

        }

    }
);
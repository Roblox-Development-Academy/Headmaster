const path = require('path');
const MiniCssExtractPlugin = require('mini-css-extract-plugin');

require('dotenv').config({
    path: path.join(__dirname, ".env")
});

const isDevelopment = process.env.NODE_ENV === "development";

console.log("Running with mode", process.env.NODE_ENV);
module.exports = {
    mode: process.env.NODE_ENV,
    entry: {
        date_select: "./web/src/date_select.js",
        staff_application: './web/src/staff_application.js',
    },
    devtool: 'inline-source-map',
    plugins: [
        new MiniCssExtractPlugin()
    ],
    output: {
        filename: '[name].js',
        path: path.resolve(__dirname, './web/static'),
    },
    module: {
        rules: [
            {
                test: /\.s[ac]ss$/i,
                use: [
                    // Creates `style` nodes from JS strings
                    isDevelopment ? "style-loader" : MiniCssExtractPlugin.loader,
                    // Translates CSS into CommonJS
                    {
                        loader: "css-loader",
                        options: {
                            sourceMap: isDevelopment,
                        }
                    },
                    // Compiles Sass to CSS
                    {
                        loader: "sass-loader",
                        options: {
                            sourceMap: isDevelopment
                        }
                    }
                ],
            },
        ],
    }
};